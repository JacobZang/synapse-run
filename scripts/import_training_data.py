#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
训练数据导入脚本 - 使用SQLAlchemy ORM安全导入
从Excel文件导入训练记录到MySQL数据库

使用方法:
1. 确保数据库已创建training_records表
2. 配置config.py中的数据库连接参数
3. 运行: python scripts/import_training_data.py

功能:
- 使用SQLAlchemy ORM避免SQL注入风险
- 自动解析Excel文件
- 数据清洗(处理NaN值、时间格式转换)
- 批量导入到数据库
- 支持覆盖写入模式(TRUNCATE TABLE)
"""

import os
import sys
import pandas as pd
from datetime import datetime
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 导入必需模块
import config
from models.training_record import TrainingRecord, Base
from sqlalchemy import create_engine


class TrainingDataImporter:
    """训练数据导入器 - 使用SQLAlchemy ORM"""

    def __init__(self, excel_path: str, db_engine=None):
        """
        初始化导入器

        Args:
            excel_path: Excel文件路径
            db_engine: SQLAlchemy引擎,如果为None则直接从config构建
        """
        self.excel_path = excel_path

        if db_engine:
            self.engine = db_engine
        else:
            # 直接从config构建引擎,避免importlib.reload的不确定性
            connection_string = (
                f'mysql+pymysql://{config.DB_USER}:{config.DB_PASSWORD}'
                f'@{config.DB_HOST}:{config.DB_PORT}/{config.DB_NAME}'
                f'?charset={config.DB_CHARSET}'
            )
            self.engine = create_engine(
                connection_string,
                pool_pre_ping=True,
                pool_recycle=3600,
                echo=False
            )

        self.SessionLocal = sessionmaker(bind=self.engine, autoflush=False, autocommit=False)

    def load_excel(self) -> pd.DataFrame:
        """加载Excel文件"""
        print(f"[1/4] 加载Excel文件: {self.excel_path}")
        if not os.path.exists(self.excel_path):
            raise FileNotFoundError(f"Excel文件不存在: {self.excel_path}")

        # 读取Excel,排除运动轨迹列
        df = pd.read_excel(self.excel_path)
        print(f"   原始列: {df.columns.tolist()}")

        # 删除运动轨迹列
        if '运动轨迹' in df.columns:
            df = df.drop(columns=['运动轨迹'])
            print("   已删除'运动轨迹'列")

        print(f"   加载 {len(df)} 条记录")
        return df

    def clean_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """数据清洗"""
        print("[2/4] 数据清洗中...")

        # 处理NaN值
        df = df.fillna({
            '运动时长(秒)': 0,
            '卡路里': 0,
            '运动距离(米)': 0.0,
            '平均心率': 0,
            '最大心率': 0,
            '心率记录': '[]'
        })

        # 转换数据类型
        df['运动时长(秒)'] = df['运动时长(秒)'].astype(int)
        df['卡路里'] = df['卡路里'].astype(int)
        df['运动距离(米)'] = df['运动距离(米)'].astype(float)
        df['平均心率'] = df['平均心率'].astype(int)
        df['最大心率'] = df['最大心率'].astype(int)

        # 时间格式统一
        df['开始时间'] = pd.to_datetime(df['开始时间'])
        df['结束时间'] = pd.to_datetime(df['结束时间'])

        print(f"   清洗完成, 有效记录: {len(df)}")
        return df

    def create_table_if_not_exists(self):
        """如果表不存在则创建"""
        print("[3/4] 检查数据库表...")
        Base.metadata.create_all(bind=self.engine)
        print("   表结构检查完成")

    def import_to_db(self, df: pd.DataFrame, truncate_first: bool = False):
        """
        导入数据到数据库 - 使用SQLAlchemy ORM

        Args:
            df: 待导入的DataFrame
            truncate_first: 是否先清空表(覆盖写入模式)

        Returns:
            dict: 导入结果统计 {'success': int, 'failed': int, 'total': int}
        """
        print("[4/4] 导入数据到数据库...")

        # 创建表(如果不存在)
        self.create_table_if_not_exists()

        session = self.SessionLocal()
        try:
            # 覆盖写入模式:先清��表
            if truncate_first:
                print("   覆盖写入模式:清空现有数据...")
                session.query(TrainingRecord).delete()
                session.commit()
                print("   数据清空完成")

            now_ts = int(datetime.now().timestamp())
            success_count = 0
            failed_count = 0
            batch_records = []

            for idx, row in df.iterrows():
                try:
                    # 使用ORM模型创建记录
                    record = TrainingRecord(
                        user_id='default_user',
                        exercise_type=row['运动类型'],
                        duration_seconds=int(row['运动时长(秒)']),
                        start_time=row['开始时间'].to_pydatetime(),
                        end_time=row['结束时间'].to_pydatetime(),
                        calories=int(row['卡路里']) if pd.notna(row['卡路里']) else None,
                        distance_meters=float(row['运动距离(米)']) if pd.notna(row['运动距离(米)']) else None,
                        avg_heart_rate=int(row['平均心率']) if pd.notna(row['平均心率']) else None,
                        max_heart_rate=int(row['最大心率']) if pd.notna(row['最大心率']) else None,
                        heart_rate_data=str(row['心率记录']) if pd.notna(row['心率记录']) else '[]',
                        add_ts=now_ts,
                        last_modify_ts=now_ts,
                        data_source='excel_import'
                    )

                    batch_records.append(record)
                    success_count += 1

                    # 批量提交(每100条)
                    if len(batch_records) >= 100:
                        session.bulk_save_objects(batch_records)
                        session.commit()
                        print(f"   已处理 {success_count}/{len(df)} 条记录...")
                        batch_records = []

                except Exception as e:
                    failed_count += 1
                    print(f"   第{idx+1}行导入失败: {e}")
                    session.rollback()

            # 提交剩余记录
            if batch_records:
                session.bulk_save_objects(batch_records)
                session.commit()

            print(f"\n导入完成!")
            print(f"   成功: {success_count} 条")
            print(f"   失败: {failed_count} 条")

            return {
                'success': success_count,
                'failed': failed_count,
                'total': len(df)
            }

        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def run(self, truncate_first: bool = False):
        """
        执行完整导入流程

        Args:
            truncate_first: 是否覆盖写入(先清空表)

        Returns:
            dict: 导入结果统计
        """
        print("="*80)
        print("训练数据导入工具 (SQLAlchemy ORM)")
        print("="*80)

        try:
            # 加载Excel
            df = self.load_excel()

            # 清洗数据
            df = self.clean_data(df)

            # 导入数据库
            result = self.import_to_db(df, truncate_first=truncate_first)

            print("\n✅ 导入成功!")
            return result

        except Exception as e:
            print(f"\n❌ 导入失败: {e}")
            import traceback
            traceback.print_exc()
            raise  # 重新抛出异常供调用方处理


def main():
    """主函数"""
    # Excel文件路径
    excel_path = Path(project_root) / "data" / "406099.xlsx"

    # 检查文件是否存在
    if not excel_path.exists():
        print(f"错误: Excel文件不存在 - {excel_path}")
        print("请将406099.xlsx文件放在 data/ 目录下")
        sys.exit(1)

    # 执行导入
    importer = TrainingDataImporter(str(excel_path))
    importer.run()


if __name__ == "__main__":
    main()

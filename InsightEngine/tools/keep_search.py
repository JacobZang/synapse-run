# -*- coding: utf-8 -*-
"""
Keep运动APP训练数据搜索工具
基于training_records_keep表的数据查询实现
"""

import os
import json
import pymysql
import pymysql.cursors
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .base_search import BaseTrainingDataSearch, DBResponse


@dataclass
class KeepTrainingRecord:
    """Keep训练记录数据类 - 对应training_records_keep表结构"""
    id: int
    user_id: str

    # 基础训练信息
    exercise_type: str
    duration_seconds: int
    start_time: datetime
    end_time: datetime

    # 运动指标
    calories: Optional[int]
    distance_meters: Optional[float]
    avg_heart_rate: Optional[int]
    max_heart_rate: Optional[int]

    # 详细数据 (JSON格式)
    heart_rate_data: Optional[List[int]]

    # 元数据
    add_ts: int
    last_modify_ts: int
    data_source: str

    # 计算字段
    pace_per_km: Optional[float] = None


class KeepDataSearch(BaseTrainingDataSearch):
    """Keep数据源搜索工具"""

    def __init__(self):
        super().__init__(data_source="keep")

    def _load_db_config(self) -> Dict[str, Any]:
        """从环境变量加载数据库配置"""
        return {
            'host': os.getenv("DB_HOST"),
            'user': os.getenv("DB_USER"),
            'password': os.getenv("DB_PASSWORD"),
            'db': os.getenv("DB_NAME"),
            'port': int(os.getenv("DB_PORT", 3306)),
            'charset': os.getenv("DB_CHARSET", "utf8mb4"),
            'cursorclass': pymysql.cursors.DictCursor
        }

    def _validate_config(self):
        """验证配��完整性"""
        required = ['host', 'user', 'password', 'db']
        if missing := [k for k in required if not self.db_config[k]]:
            raise ValueError(
                f"Keep数据源配置缺失! 请设置环境变量: {', '.join([f'DB_{k.upper()}' for k in missing])}"
            )

    def _execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行SQL查询"""
        conn = None
        try:
            conn = pymysql.connect(**self.db_config)
            with conn.cursor() as cursor:
                cursor.execute(query, params or ())
                return cursor.fetchall()
        except pymysql.Error as e:
            print(f"Keep数据源查询错误: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def _parse_heart_rate_data(self, hr_json: Optional[str]) -> Optional[List[int]]:
        """解析心率JSON数据"""
        if not hr_json:
            return None
        try:
            data = json.loads(hr_json)
            if data is None or not isinstance(data, (list, tuple)):
                return None
            result = []
            for x in data:
                if x is not None and x != '':
                    try:
                        result.append(int(x))
                    except (ValueError, TypeError):
                        continue
            return result if result else None
        except (json.JSONDecodeError, ValueError, TypeError):
            return None

    def _row_to_record(self, row: Dict[str, Any]) -> KeepTrainingRecord:
        """将数据库行转换为KeepTrainingRecord对象"""
        pace = self._calculate_pace(row['duration_seconds'], row.get('distance_meters'))
        return KeepTrainingRecord(
            id=row['id'],
            user_id=row.get('user_id', 'default_user'),
            exercise_type=row['exercise_type'],
            duration_seconds=row['duration_seconds'],
            start_time=row['start_time'],
            end_time=row['end_time'],
            calories=row.get('calories'),
            distance_meters=row.get('distance_meters'),
            avg_heart_rate=row.get('avg_heart_rate'),
            max_heart_rate=row.get('max_heart_rate'),
            heart_rate_data=self._parse_heart_rate_data(row.get('heart_rate_data')),
            add_ts=row['add_ts'],
            last_modify_ts=row['last_modify_ts'],
            data_source=row.get('data_source', 'keep_import'),
            pace_per_km=pace
        )

    def search_recent_trainings(
        self,
        days: int = 7,
        exercise_type: Optional[str] = None,
        limit: int = 50
    ) -> DBResponse:
        """查询最近训练记录"""
        params_for_log = {'days': days, 'exercise_type': exercise_type, 'limit': limit}
        print(f"--- Keep数据源: 查询最近训练记录 (params: {params_for_log}) ---")

        start_time = datetime.now() - timedelta(days=days)
        query = """
            SELECT * FROM training_records_keep
            WHERE start_time >= %s
        """
        params = [start_time]

        if exercise_type:
            query += " AND exercise_type = %s"
            params.append(exercise_type)

        query += " ORDER BY start_time DESC LIMIT %s"
        params.append(limit)

        raw_results = self._execute_query(query, tuple(params))
        records = [self._row_to_record(row) for row in raw_results]

        return DBResponse(
            tool_name="search_recent_trainings",
            parameters=params_for_log,
            data_source=self.data_source,
            results=records,
            results_count=len(records)
        )

    def search_by_date_range(
        self,
        start_date: str,
        end_date: str,
        exercise_type: Optional[str] = None,
        limit: int = 100
    ) -> DBResponse:
        """按日期范围查询"""
        params_for_log = {
            'start_date': start_date,
            'end_date': end_date,
            'exercise_type': exercise_type,
            'limit': limit
        }
        print(f"--- Keep数据源: 按日期范围查询 (params: {params_for_log}) ---")

        try:
            start_dt = datetime.strptime(start_date, '%Y-%m-%d')
            end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
        except ValueError:
            return DBResponse(
                tool_name="search_by_date_range",
                parameters=params_for_log,
                data_source=self.data_source,
                error_message="日期格式错误,请使用 'YYYY-MM-DD' 格式"
            )

        query = """
            SELECT * FROM training_records_keep
            WHERE start_time >= %s AND start_time < %s
        """
        params = [start_dt, end_dt]

        if exercise_type:
            query += " AND exercise_type = %s"
            params.append(exercise_type)

        query += " ORDER BY start_time DESC LIMIT %s"
        params.append(limit)

        raw_results = self._execute_query(query, tuple(params))
        records = [self._row_to_record(row) for row in raw_results]

        return DBResponse(
            tool_name="search_by_date_range",
            parameters=params_for_log,
            data_source=self.data_source,
            results=records
        )

    def get_training_stats(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exercise_type: Optional[str] = None
    ) -> DBResponse:
        """获取训练统计"""
        params_for_log = {
            'start_date': start_date,
            'end_date': end_date,
            'exercise_type': exercise_type
        }
        print(f"--- Keep数据源: 获取训练统计 (params: {params_for_log}) ---")

        query = """
            SELECT
                COUNT(*) as total_sessions,
                SUM(duration_seconds) as total_duration,
                AVG(duration_seconds) as avg_duration,
                SUM(distance_meters) as total_distance,
                AVG(distance_meters) as avg_distance,
                AVG(avg_heart_rate) as overall_avg_heart_rate,
                MAX(max_heart_rate) as peak_heart_rate,
                SUM(calories) as total_calories
            FROM training_records_keep
            WHERE 1=1
        """
        params = []

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query += " AND start_time >= %s"
                params.append(start_dt)
            except ValueError:
                return DBResponse(
                    tool_name="get_training_stats",
                    parameters=params_for_log,
                    data_source=self.data_source,
                    error_message="开始日期格式错误"
                )

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query += " AND start_time < %s"
                params.append(end_dt)
            except ValueError:
                return DBResponse(
                    tool_name="get_training_stats",
                    parameters=params_for_log,
                    data_source=self.data_source,
                    error_message="结束日期格式错误"
                )

        if exercise_type:
            query += " AND exercise_type = %s"
            params.append(exercise_type)

        raw_results = self._execute_query(query, tuple(params))
        if not raw_results:
            return DBResponse(
                tool_name="get_training_stats",
                parameters=params_for_log,
                data_source=self.data_source,
                error_message="未找到数据"
            )

        stats = raw_results[0]
        # 计算平均配速
        if stats['total_distance'] and stats['total_distance'] > 0:
            total_distance_km = float(stats['total_distance']) / 1000.0
            total_duration = float(stats['total_duration']) if stats['total_duration'] else 0.0
            avg_pace = total_duration / total_distance_km
            stats['avg_pace_per_km'] = round(avg_pace, 2)
        else:
            stats['avg_pace_per_km'] = None

        return DBResponse(
            tool_name="get_training_stats",
            parameters=params_for_log,
            data_source=self.data_source,
            statistics=stats
        )

    def search_by_distance_range(
        self,
        min_distance_km: float,
        max_distance_km: Optional[float] = None,
        exercise_type: Optional[str] = None,
        limit: int = 50
    ) -> DBResponse:
        """按距离范围查询"""
        params_for_log = {
            'min_distance_km': min_distance_km,
            'max_distance_km': max_distance_km,
            'exercise_type': exercise_type,
            'limit': limit
        }
        print(f"--- Keep数据源: 按距离范围查询 (params: {params_for_log}) ---")

        min_meters = min_distance_km * 1000
        query = "SELECT * FROM training_records_keep WHERE distance_meters >= %s"
        params = [min_meters]

        if max_distance_km:
            max_meters = max_distance_km * 1000
            query += " AND distance_meters <= %s"
            params.append(max_meters)

        if exercise_type:
            query += " AND exercise_type = %s"
            params.append(exercise_type)

        query += " ORDER BY distance_meters DESC LIMIT %s"
        params.append(limit)

        raw_results = self._execute_query(query, tuple(params))
        records = [self._row_to_record(row) for row in raw_results]

        return DBResponse(
            tool_name="search_by_distance_range",
            parameters=params_for_log,
            data_source=self.data_source,
            results=records
        )

    def search_by_heart_rate(
        self,
        min_avg_hr: int,
        max_avg_hr: Optional[int] = None,
        exercise_type: Optional[str] = None,
        limit: int = 50
    ) -> DBResponse:
        """按心率区间查询"""
        params_for_log = {
            'min_avg_hr': min_avg_hr,
            'max_avg_hr': max_avg_hr,
            'exercise_type': exercise_type,
            'limit': limit
        }
        print(f"--- Keep数据源: 按心率区间查询 (params: {params_for_log}) ---")

        query = "SELECT * FROM training_records_keep WHERE avg_heart_rate >= %s"
        params = [min_avg_hr]

        if max_avg_hr:
            query += " AND avg_heart_rate <= %s"
            params.append(max_avg_hr)

        if exercise_type:
            query += " AND exercise_type = %s"
            params.append(exercise_type)

        query += " ORDER BY start_time DESC LIMIT %s"
        params.append(limit)

        raw_results = self._execute_query(query, tuple(params))
        records = [self._row_to_record(row) for row in raw_results]

        return DBResponse(
            tool_name="search_by_heart_rate",
            parameters=params_for_log,
            data_source=self.data_source,
            results=records
        )

    def get_exercise_type_summary(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> DBResponse:
        """按运动类型汇总"""
        params_for_log = {'start_date': start_date, 'end_date': end_date}
        print(f"--- Keep数据源: 按运动类型汇总 (params: {params_for_log}) ---")

        query = """
            SELECT
                exercise_type,
                COUNT(*) as sessions,
                SUM(duration_seconds) as total_duration,
                SUM(distance_meters) as total_distance,
                AVG(avg_heart_rate) as avg_heart_rate
            FROM training_records_keep
            WHERE 1=1
        """
        params = []

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query += " AND start_time >= %s"
                params.append(start_dt)
            except ValueError:
                return DBResponse(
                    tool_name="get_exercise_type_summary",
                    parameters=params_for_log,
                    data_source=self.data_source,
                    error_message="开始日期格式错误"
                )

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query += " AND start_time < %s"
                params.append(end_dt)
            except ValueError:
                return DBResponse(
                    tool_name="get_exercise_type_summary",
                    parameters=params_for_log,
                    data_source=self.data_source,
                    error_message="结束日期格式错误"
                )

        query += " GROUP BY exercise_type ORDER BY sessions DESC"

        raw_results = self._execute_query(query, tuple(params))
        return DBResponse(
            tool_name="get_exercise_type_summary",
            parameters=params_for_log,
            data_source=self.data_source,
            statistics={'by_type': raw_results}
        )

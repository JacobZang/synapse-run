# -*- coding: utf-8 -*-
"""
Garmin设备训练数据搜索工具
基于training_records_garmin表的数据查询实现
支持Garmin丰富的训练指标:心率区间、步频步幅、功率、训练效果等
"""

import os
import pymysql
import pymysql.cursors
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from .base_search import BaseTrainingDataSearch, DBResponse


@dataclass
class GarminTrainingRecord:
    """Garmin训练记录数据类 - 对应training_records_garmin表结构"""
    id: int
    user_id: str

    # 基础训练信息
    activity_id: Optional[str]
    activity_name: Optional[str]
    sport_type: str
    start_time_gmt: datetime
    end_time_gmt: datetime
    duration_seconds: int
    distance_meters: Optional[float]

    # 心率指标
    avg_heart_rate: Optional[int]
    max_heart_rate: Optional[int]
    hr_zone_1_seconds: Optional[int]
    hr_zone_2_seconds: Optional[int]
    hr_zone_3_seconds: Optional[int]
    hr_zone_4_seconds: Optional[int]
    hr_zone_5_seconds: Optional[int]

    # 步频步幅指标
    avg_cadence: Optional[int]
    max_cadence: Optional[int]
    avg_stride_length_cm: Optional[float]
    avg_vertical_oscillation_cm: Optional[float]
    avg_ground_contact_time_ms: Optional[int]
    vertical_ratio_percent: Optional[float]
    total_steps: Optional[int]

    # 功率指标
    avg_power_watts: Optional[int]
    max_power_watts: Optional[int]
    normalized_power_watts: Optional[int]
    power_zone_1_seconds: Optional[int]
    power_zone_2_seconds: Optional[int]
    power_zone_3_seconds: Optional[int]
    power_zone_4_seconds: Optional[int]
    power_zone_5_seconds: Optional[int]

    # 速度指标
    avg_speed_mps: Optional[float]
    max_speed_mps: Optional[float]

    # 训练效果指标
    aerobic_training_effect: Optional[float]
    anaerobic_training_effect: Optional[float]
    training_effect_label: Optional[str]
    training_load: Optional[int]

    # 卡路里和代谢指标
    activity_calories: Optional[int]
    basal_metabolism_calories: Optional[int]
    estimated_sweat_loss_ml: Optional[int]

    # 强度时长
    moderate_intensity_minutes: Optional[int]
    vigorous_intensity_minutes: Optional[int]

    # 其他指标
    body_battery_change: Optional[int]

    # 元数据
    add_ts: int
    last_modify_ts: int
    data_source: str

    # 计算字段
    pace_per_km: Optional[float] = None


class GarminDataSearch(BaseTrainingDataSearch):
    """Garmin数据源搜索工具"""

    def __init__(self):
        super().__init__(data_source="garmin")

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
        """验证配置完整性"""
        required = ['host', 'user', 'password', 'db']
        if missing := [k for k in required if not self.db_config[k]]:
            raise ValueError(
                f"Garmin数据源配置缺失! 请设置环境变量: {', '.join([f'DB_{k.upper()}' for k in missing])}"
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
            print(f"Garmin数据源查询错误: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def _row_to_record(self, row: Dict[str, Any]) -> GarminTrainingRecord:
        """将数据库行转换为GarminTrainingRecord对象"""
        pace = self._calculate_pace(row['duration_seconds'], row.get('distance_meters'))
        return GarminTrainingRecord(
            id=row['id'],
            user_id=row.get('user_id', 'default_user'),
            activity_id=row.get('activity_id'),
            activity_name=row.get('activity_name'),
            sport_type=row['sport_type'],
            start_time_gmt=row['start_time_gmt'],
            end_time_gmt=row['end_time_gmt'],
            duration_seconds=row['duration_seconds'],
            distance_meters=row.get('distance_meters'),
            # 心率指标
            avg_heart_rate=row.get('avg_heart_rate'),
            max_heart_rate=row.get('max_heart_rate'),
            hr_zone_1_seconds=row.get('hr_zone_1_seconds'),
            hr_zone_2_seconds=row.get('hr_zone_2_seconds'),
            hr_zone_3_seconds=row.get('hr_zone_3_seconds'),
            hr_zone_4_seconds=row.get('hr_zone_4_seconds'),
            hr_zone_5_seconds=row.get('hr_zone_5_seconds'),
            # 步频步幅指标
            avg_cadence=row.get('avg_cadence'),
            max_cadence=row.get('max_cadence'),
            avg_stride_length_cm=row.get('avg_stride_length_cm'),
            avg_vertical_oscillation_cm=row.get('avg_vertical_oscillation_cm'),
            avg_ground_contact_time_ms=row.get('avg_ground_contact_time_ms'),
            vertical_ratio_percent=row.get('vertical_ratio_percent'),
            total_steps=row.get('total_steps'),
            # 功率指标
            avg_power_watts=row.get('avg_power_watts'),
            max_power_watts=row.get('max_power_watts'),
            normalized_power_watts=row.get('normalized_power_watts'),
            power_zone_1_seconds=row.get('power_zone_1_seconds'),
            power_zone_2_seconds=row.get('power_zone_2_seconds'),
            power_zone_3_seconds=row.get('power_zone_3_seconds'),
            power_zone_4_seconds=row.get('power_zone_4_seconds'),
            power_zone_5_seconds=row.get('power_zone_5_seconds'),
            # 速度指标
            avg_speed_mps=row.get('avg_speed_mps'),
            max_speed_mps=row.get('max_speed_mps'),
            # 训练效果指标
            aerobic_training_effect=row.get('aerobic_training_effect'),
            anaerobic_training_effect=row.get('anaerobic_training_effect'),
            training_effect_label=row.get('training_effect_label'),
            training_load=row.get('training_load'),
            # 卡路里和代谢指标
            activity_calories=row.get('activity_calories'),
            basal_metabolism_calories=row.get('basal_metabolism_calories'),
            estimated_sweat_loss_ml=row.get('estimated_sweat_loss_ml'),
            # 强度时长
            moderate_intensity_minutes=row.get('moderate_intensity_minutes'),
            vigorous_intensity_minutes=row.get('vigorous_intensity_minutes'),
            # 其他指标
            body_battery_change=row.get('body_battery_change'),
            # 元数据
            add_ts=row['add_ts'],
            last_modify_ts=row['last_modify_ts'],
            data_source=row.get('data_source', 'garmin_import'),
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
        print(f"--- Garmin数据源: 查询最近训练记录 (params: {params_for_log}) ---")

        start_time = datetime.now() - timedelta(days=days)
        query = """
            SELECT * FROM training_records_garmin
            WHERE start_time_gmt >= %s
        """
        params = [start_time]

        if exercise_type:
            query += " AND sport_type = %s"
            params.append(exercise_type)

        query += " ORDER BY start_time_gmt DESC LIMIT %s"
        params.append(limit)

        raw_results = self._execute_query(query, tuple(params))
        records = [self._row_to_record(row) for row in raw_results]

        return DBResponse(
            tool_name="search_recent_trainings",
            parameters=params_for_log,
            data_source=self.data_source,
            results=records
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
        print(f"--- Garmin数据源: 按日期范围查询 (params: {params_for_log}) ---")

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
            SELECT * FROM training_records_garmin
            WHERE start_time_gmt >= %s AND start_time_gmt < %s
        """
        params = [start_dt, end_dt]

        if exercise_type:
            query += " AND sport_type = %s"
            params.append(exercise_type)

        query += " ORDER BY start_time_gmt DESC LIMIT %s"
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
        """获取训练统计(包含Garmin扩展指标)"""
        params_for_log = {
            'start_date': start_date,
            'end_date': end_date,
            'exercise_type': exercise_type
        }
        print(f"--- Garmin数据源: 获取训练统计 (params: {params_for_log}) ---")

        query = """
            SELECT
                COUNT(*) as total_sessions,
                SUM(duration_seconds) as total_duration,
                AVG(duration_seconds) as avg_duration,
                SUM(distance_meters) as total_distance,
                AVG(distance_meters) as avg_distance,
                AVG(avg_heart_rate) as overall_avg_heart_rate,
                MAX(max_heart_rate) as peak_heart_rate,
                AVG(avg_cadence) as overall_avg_cadence,
                AVG(avg_power_watts) as overall_avg_power,
                AVG(training_load) as avg_training_load,
                AVG(aerobic_training_effect) as avg_aerobic_effect,
                AVG(anaerobic_training_effect) as avg_anaerobic_effect,
                SUM(activity_calories) as total_calories,
                AVG(avg_stride_length_cm) as avg_stride_length,
                AVG(avg_vertical_oscillation_cm) as avg_vertical_oscillation,
                AVG(avg_ground_contact_time_ms) as avg_ground_contact_time
            FROM training_records_garmin
            WHERE 1=1
        """
        params = []

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query += " AND start_time_gmt >= %s"
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
                query += " AND start_time_gmt < %s"
                params.append(end_dt)
            except ValueError:
                return DBResponse(
                    tool_name="get_training_stats",
                    parameters=params_for_log,
                    data_source=self.data_source,
                    error_message="结束日期格式错误"
                )

        if exercise_type:
            query += " AND sport_type = %s"
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
        print(f"--- Garmin数据源: 按距离范围查询 (params: {params_for_log}) ---")

        min_meters = min_distance_km * 1000
        query = "SELECT * FROM training_records_garmin WHERE distance_meters >= %s"
        params = [min_meters]

        if max_distance_km:
            max_meters = max_distance_km * 1000
            query += " AND distance_meters <= %s"
            params.append(max_meters)

        if exercise_type:
            query += " AND sport_type = %s"
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
        print(f"--- Garmin数据源: 按心率区间查询 (params: {params_for_log}) ---")

        query = "SELECT * FROM training_records_garmin WHERE avg_heart_rate >= %s"
        params = [min_avg_hr]

        if max_avg_hr:
            query += " AND avg_heart_rate <= %s"
            params.append(max_avg_hr)

        if exercise_type:
            query += " AND sport_type = %s"
            params.append(exercise_type)

        query += " ORDER BY start_time_gmt DESC LIMIT %s"
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
        """按运动类型汇总(包含Garmin扩展统计)"""
        params_for_log = {'start_date': start_date, 'end_date': end_date}
        print(f"--- Garmin数据源: 按运动类型汇总 (params: {params_for_log}) ---")

        query = """
            SELECT
                sport_type,
                COUNT(*) as sessions,
                SUM(duration_seconds) as total_duration,
                SUM(distance_meters) as total_distance,
                AVG(avg_heart_rate) as avg_heart_rate,
                AVG(avg_cadence) as avg_cadence,
                AVG(avg_power_watts) as avg_power,
                AVG(training_load) as avg_training_load
            FROM training_records_garmin
            WHERE 1=1
        """
        params = []

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query += " AND start_time_gmt >= %s"
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
                query += " AND start_time_gmt < %s"
                params.append(end_dt)
            except ValueError:
                return DBResponse(
                    tool_name="get_exercise_type_summary",
                    parameters=params_for_log,
                    data_source=self.data_source,
                    error_message="结束日期格式错误"
                )

        query += " GROUP BY sport_type ORDER BY sessions DESC"

        raw_results = self._execute_query(query, tuple(params))
        return DBResponse(
            tool_name="get_exercise_type_summary",
            parameters=params_for_log,
            data_source=self.data_source,
            statistics={'by_type': raw_results}
        )

    # ===== Garmin专属扩展工具 =====

    def search_by_training_load(
        self,
        min_load: int,
        max_load: Optional[int] = None,
        limit: int = 50
    ) -> DBResponse:
        """按训练负荷查询 (Garmin专属)"""
        params_for_log = {
            'min_load': min_load,
            'max_load': max_load,
            'limit': limit
        }
        print(f"--- Garmin数据源: 按训练负荷查询 (params: {params_for_log}) ---")

        query = "SELECT * FROM training_records_garmin WHERE training_load >= %s"
        params = [min_load]

        if max_load:
            query += " AND training_load <= %s"
            params.append(max_load)

        query += " ORDER BY training_load DESC LIMIT %s"
        params.append(limit)

        raw_results = self._execute_query(query, tuple(params))
        records = [self._row_to_record(row) for row in raw_results]

        return DBResponse(
            tool_name="search_by_training_load",
            parameters=params_for_log,
            data_source=self.data_source,
            results=records
        )

    def search_by_power_zone(
        self,
        min_avg_power: int,
        max_avg_power: Optional[int] = None,
        limit: int = 50
    ) -> DBResponse:
        """按功率区间查询 (Garmin专属)"""
        params_for_log = {
            'min_avg_power': min_avg_power,
            'max_avg_power': max_avg_power,
            'limit': limit
        }
        print(f"--- Garmin数据源: 按功率区间查询 (params: {params_for_log}) ---")

        query = "SELECT * FROM training_records_garmin WHERE avg_power_watts >= %s"
        params = [min_avg_power]

        if max_avg_power:
            query += " AND avg_power_watts <= %s"
            params.append(max_avg_power)

        query += " ORDER BY avg_power_watts DESC LIMIT %s"
        params.append(limit)

        raw_results = self._execute_query(query, tuple(params))
        records = [self._row_to_record(row) for row in raw_results]

        return DBResponse(
            tool_name="search_by_power_zone",
            parameters=params_for_log,
            data_source=self.data_source,
            results=records
        )

    def get_training_effect_analysis(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> DBResponse:
        """获取训练效果分析 (Garmin专属)"""
        params_for_log = {'start_date': start_date, 'end_date': end_date}
        print(f"--- Garmin数据源: 训练效果分析 (params: {params_for_log}) ---")

        query = """
            SELECT
                COUNT(*) as total_sessions,
                AVG(aerobic_training_effect) as avg_aerobic_effect,
                AVG(anaerobic_training_effect) as avg_anaerobic_effect,
                AVG(training_load) as avg_training_load,
                SUM(CASE WHEN training_effect_label LIKE '%Maintaining%' THEN 1 ELSE 0 END) as maintaining_count,
                SUM(CASE WHEN training_effect_label LIKE '%Improving%' THEN 1 ELSE 0 END) as improving_count,
                SUM(CASE WHEN training_effect_label LIKE '%Highly Improving%' THEN 1 ELSE 0 END) as highly_improving_count,
                SUM(moderate_intensity_minutes) as total_moderate_minutes,
                SUM(vigorous_intensity_minutes) as total_vigorous_minutes
            FROM training_records_garmin
            WHERE 1=1
        """
        params = []

        if start_date:
            try:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d')
                query += " AND start_time_gmt >= %s"
                params.append(start_dt)
            except ValueError:
                return DBResponse(
                    tool_name="get_training_effect_analysis",
                    parameters=params_for_log,
                    data_source=self.data_source,
                    error_message="开始日期格式错误"
                )

        if end_date:
            try:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
                query += " AND start_time_gmt < %s"
                params.append(end_dt)
            except ValueError:
                return DBResponse(
                    tool_name="get_training_effect_analysis",
                    parameters=params_for_log,
                    data_source=self.data_source,
                    error_message="结束日期格式错误"
                )

        raw_results = self._execute_query(query, tuple(params))
        if not raw_results:
            return DBResponse(
                tool_name="get_training_effect_analysis",
                parameters=params_for_log,
                data_source=self.data_source,
                error_message="未找到数据"
            )

        return DBResponse(
            tool_name="get_training_effect_analysis",
            parameters=params_for_log,
            data_source=self.data_source,
            statistics=raw_results[0]
        )

    def get_supported_tools(self) -> List[str]:
        """获取Garmin数据源支持的所有工具"""
        base_tools = super().get_supported_tools()
        garmin_tools = [
            "search_by_training_load",
            "search_by_power_zone",
            "get_training_effect_analysis"
        ]
        return base_tools + garmin_tools

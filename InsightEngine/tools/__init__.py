"""
InsightEngine 训练数据搜索工具模块

提供多数据源(Keep/Garmin)的训练数据查询功能

使用示例:
    >>> # 方式1: 自动从config.py读取数据源
    >>> from InsightEngine.tools import create_training_data_search
    >>> search_tool = create_training_data_search()
    >>>
    >>> # 方式2: 手动指定数据源
    >>> keep_tool = create_training_data_search('keep')
    >>> garmin_tool = create_training_data_search('garmin')
    >>>
    >>> # 方式3: 向后兼容模式(推荐用于旧代码迁移)
    >>> from InsightEngine.tools import TrainingDataDB
    >>> db = TrainingDataDB()  # 自动选择数据源
"""

# ===== 核心工厂和便捷函数 =====
from .factory import (
    TrainingDataSearchFactory,
    create_training_data_search,
    TrainingDataDB  # 向后兼容性包装类
)

# ===== 基类和数据结构 =====
from .base_search import (
    BaseTrainingDataSearch,
    DBResponse
)

# ===== 数据源实现类 =====
from .keep_search import (
    KeepDataSearch,
    KeepTrainingRecord
)

from .garmin_search import (
    GarminDataSearch,
    GarminTrainingRecord
)

# ===== 导出列表 =====
__all__ = [
    # 工厂和便捷函数 (推荐使用)
    "TrainingDataSearchFactory",
    "create_training_data_search",
    "TrainingDataDB",  # 向后兼容

    # 基类和通用类型
    "BaseTrainingDataSearch",
    "DBResponse",

    # Keep数据源
    "KeepDataSearch",
    "KeepTrainingRecord",

    # Garmin数据源
    "GarminDataSearch",
    "GarminTrainingRecord",
]

# ===== 版本信息 =====
__version__ = "2.0.0"
__author__ = "BettaFish Team"
__description__ = "Multi-source training data search tools for InsightEngine"

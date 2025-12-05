"""
后勤与情报官Agent
专注于收集比赛报名、天气预报、装备价格、路线坡度等实用情报的AI代理
"""

from .agent import LogisticsIntelligenceAgent, create_agent
# 向后兼容的别名
DeepSearchAgent = LogisticsIntelligenceAgent

from .utils.config import Config, load_config

__version__ = "1.0.0"
__author__ = "Logistics Intelligence Agent Team"

__all__ = ["LogisticsIntelligenceAgent", "DeepSearchAgent", "create_agent", "Config", "load_config"]

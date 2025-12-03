# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

"微舆"(BettaFish) 是一个基于多智能体架构的舆情分析系统,采用纯Python模块化设计。系统通过四个专业Agent协同工作,实现从数据爬取、多模态分析到智能报告生成的完整舆情分析流程。

**核心技术栈**: Python 3.9+, Flask, Streamlit, OpenAI-compatible LLM APIs, MySQL, Playwright

## 系统架构

### 多智能体协作架构

系统由四个核心Agent组成,每个Agent拥有独立的工具集、提示词模板和处理节点:

1. **Query Agent** (`QueryEngine/`): 国内外新闻广度搜索
   - 工具: Tavily API (新闻搜索、网页搜索等6种工具)
   - LLM推荐: DeepSeek Reasoner
   - 核心能力: 互联网信息检索、事件追踪

2. **Media Agent** (`MediaEngine/`): 多模态内容深度分析
   - 工具: 视频分析、图像OCR、结构化信息提取
   - LLM推荐: Gemini 2.5 Pro
   - 核心能力: 短视频理解、搜索结果卡片解析

3. **Insight Agent** (`InsightEngine/`): 私有数据库深度挖掘
   - 工具: MediaCrawlerDB (5种本地数据库查询工具)
   - 中间件: Qwen关键词优化器、多语言情感分析器
   - LLM推荐: Kimi K2
   - 核心能力: 数据库查询、情感分析、统计建模

4. **Report Agent** (`ReportEngine/`): 智能报告生成
   - 工具: 模板选择引擎、HTML生成器
   - LLM推荐: Gemini 2.5 Pro
   - 核心能力: 报告模板动态选择、多轮报告优化

### ForumEngine 论坛协作机制

**核心创新**: Agent间通过"论坛"机制进行思维碰撞与辩论

- **监控模块** (`ForumEngine/monitor.py`): 实时监控Agent日志,提取关键发言
- **主持人模块** (`ForumEngine/llm_host.py`): LLM主持人生成总结和引导
- **论坛日志** (`logs/forum.log`): 所有Agent通过此文件交流
- **工具接口** (`utils/forum_reader.py`): Agent读取论坛内容的统一接口

工作流程:
```
1. 各Agent将分析结果写入 logs/forum.log
2. ForumEngine监控模块提取关键信息
3. 主持人LLM生成总结和下一步引导
4. 各Agent通过forum_reader工具读取论坛内容
5. 循环迭代直到达成共识或完成任务
```

### 统一Agent架构模式

所有Agent遵循相同的模块化架构:

```
<Agent>/
├── agent.py              # Agent主类,实现完整workflow
├── llms/base.py          # 统一的OpenAI兼容LLM客户端
├── nodes/                # 处理节点
│   ├── base_node.py      # 基础节点类
│   ├── search_node.py    # 搜索节点
│   ├── summary_node.py   # 总结节点
│   └── formatting_node.py # 格式化节点
├── tools/                # 专属工具集
├── state/state.py        # Agent状态管理
├── prompts/prompts.py    # 提示词模板
└── utils/config.py       # 配置管理
```

**节点职责**:
- `FirstSearchNode`: 首轮搜索,生成初步结果
- `ReflectionNode`: 反思与优化,识别信息缺口
- `SummaryNode`: 总结归纳,提取关键信息
- `FormattingNode`: 格式化输出,适配不同场景

## 关键开发指南

### 配置系统

**全局配置** (`config.py`): 数据库连接、LLM API配置、搜索API配置

**Agent配置** (`<Agent>/utils/config.py`): Agent特定参数

```python
# 数据库配置
DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME

# LLM配置 (每个Agent独立配置)
INSIGHT_ENGINE_API_KEY, BASE_URL, MODEL_NAME
MEDIA_ENGINE_API_KEY, BASE_URL, MODEL_NAME
QUERY_ENGINE_API_KEY, BASE_URL, MODEL_NAME
REPORT_ENGINE_API_KEY, BASE_URL, MODEL_NAME
FORUM_HOST_API_KEY, BASE_URL, MODEL_NAME

# 网络工具
TAVILY_API_KEY, BOCHA_WEB_SEARCH_API_KEY
```

**重要**: 所有LLM必须兼容OpenAI请求格式 (api_key + base_url + model_name)

### 常用命令

#### 启动完整系统
```bash
conda activate <your_env>
python app.py  # 启动Flask主应用,访问 http://localhost:5000
```

#### 单独启动Agent (调试用)
```bash
# 启动QueryEngine
streamlit run SingleEngineApp/query_engine_streamlit_app.py --server.port 8503

# 启动MediaEngine
streamlit run SingleEngineApp/media_engine_streamlit_app.py --server.port 8502

# 启动InsightEngine
streamlit run SingleEngineApp/insight_engine_streamlit_app.py --server.port 8501
```

#### 爬虫系统独立使用
```bash
cd MindSpider

# 初始化数据库
python schema/init_database.py

# 完整爬虫流程
python main.py --complete --date 2024-01-20

# 仅话题提取
python main.py --broad-topic --date 2024-01-20

# 仅深度爬取
python main.py --deep-sentiment --platforms xhs dy wb
```

#### 环境安装
```bash
# 基础依赖
pip install -r requirements.txt

# Playwright浏览器驱动 (爬虫必需)
playwright install chromium

# 可选: 本地情感分析 (需GPU加速)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install transformers scikit-learn xgboost
```

### LLM客户端使用

所有Agent使用统一的LLMClient (`<Agent>/llms/base.py`):

```python
from .llms import LLMClient

client = LLMClient(
    api_key=config.llm_api_key,
    base_url=config.llm_base_url,
    model_name=config.llm_model_name
)

# 同步调用
response = client.create_completion(
    prompt="你的提示词",
    temperature=0.7
)

# 异步调用
response = await client.acreate_completion(
    prompt="你的提示词"
)
```

### 情感分析模型

系统集成多种情感分析方法 (`SentimentAnalysisModel/`):

1. **多语言模型** (推荐): `WeiboMultilingualSentiment/` - 支持22种语言
2. **小参数Qwen3**: `WeiboSentiment_SmallQwen/` - 高性能中文分析
3. **BERT微调**: `WeiboSentiment_Finetuned/BertChinese-Lora/`
4. **GPT-2 LoRA**: `WeiboSentiment_Finetuned/GPT2-Lora/`
5. **传统ML**: `WeiboSentiment_MachineLearning/` - SVM/XGBoost

使用示例:
```python
from InsightEngine.tools import multilingual_sentiment_analyzer

result = multilingual_sentiment_analyzer.predict(
    text="这个产品真的很不错",
    language="zh"
)
# 返回: {'sentiment': 'positive', 'confidence': 0.95}
```

### 数据库操作

**InsightEngine工具集** (`InsightEngine/tools/search.py`):

```python
# 初始化数据库连接
search_tool = MediaCrawlerDB()

# 话题全局搜索
results = search_tool.search_topic_globally(
    keyword="武汉大学",
    limit=200
)

# 获取评论数据
comments = search_tool.get_comments_by_post_id(
    post_id="123456",
    limit=500
)

# 统计分析
stats = search_tool.get_topic_statistics(
    keyword="武汉大学",
    start_date="2024-01-01",
    end_date="2024-01-31"
)
```

### 报告模板系统

**模板位置**: `ReportEngine/report_template/`

**自定义模板**:
1. 在Web界面上传 `.md` 或 `.txt` 文件
2. 或直接在 `report_template/` 目录创建模板文件
3. Agent会自动选择最合适的模板

**模板变量**:
- `{topic}`: 分析主题
- `{date_range}`: 日期范围
- `{agent_insights}`: Agent分析结果
- `{forum_summary}`: 论坛协作总结

### 日志与调试

**日志文件位置**: `logs/`

- `forum.log`: ForumEngine论坛交流日志
- `query_agent.log`: QueryAgent运行日志
- `media_agent.log`: MediaAgent运行日志
- `insight_agent.log`: InsightAgent运行日志

**重要**: ForumEngine在每次 `app.py` 启动时会清空 `forum.log`

### 接入自定义业务数据库

1. 在 `config.py` 添加业务数据库配置
2. 创建自定义工具 `InsightEngine/tools/custom_db_tool.py`
3. 集成到 `InsightEngine/agent.py`

示例:
```python
# config.py
BUSINESS_DB_HOST = "your_host"
BUSINESS_DB_NAME = "your_database"

# InsightEngine/tools/custom_db_tool.py
class CustomBusinessDBTool:
    def search_business_data(self, query: str, table: str):
        # 实现业务逻辑
        pass

# InsightEngine/agent.py
from .tools.custom_db_tool import CustomBusinessDBTool

class DeepSearchAgent:
    def __init__(self):
        self.custom_db = CustomBusinessDBTool()
```

## 代码规范

- **编码**: 所有Python文件使用UTF-8编码,文件头添加 `# -*- coding: utf-8 -*-`
- **命名**: 遵循PEP8规范,类名大驼峰,函数名下划线
- **文档**: 每个类和函数添加docstring说明参数和返回值
- **错误处理**: 关键操作使用try-except捕获异常,记录到日志
- **类型提示**: 关键函数添加类型注解 (typing模块)

## 项目特性

### MindSpider爬虫系统

**独立配置**: 爬虫系统有独立配置文件 `MindSpider/config.py`

**数据库结构**: `MindSpider/schema/mindspider_tables.sql`

**两阶段爬取**:
1. **话题提取** (`BroadTopicExtraction/`): 从新闻源提取热点话题
2. **深度爬取** (`DeepSentimentCrawling/`): 基于话题爬取多平台数据

**支持平台**: 微博、小红书、抖音、快手、B站等10+平台

### 反思机制

所有Agent都实现了ReflectionNode,支持自我优化:

```python
class ReflectionNode:
    def execute(self, state: State) -> Dict:
        # 分析已有结果
        # 识别信息缺口
        # 生成优化建议
        # 返回下一轮搜索策略
```

### 异步与并行

- Flask主应用使用 `flask-socketio` 实现实时通信
- Agent内部使用async/await处理IO密集操作
- ForumEngine使用threading实现后台监控

## 架构决策

**为何选择Flask + Streamlit组合**:
- Flask处理主流程控制和Agent协调
- Streamlit提供快速的单Agent调试界面
- 前后端分离,易于扩展

**为何使用论坛机制**:
- 避免单一LLM的思维局限
- 通过辩论产生更高质量的集体智能
- 可追溯的决策过程记录

**为何所有LLM使用OpenAI格式**:
- 统一接口降低集成复杂度
- 便于切换不同LLM提供商
- 降低vendor lock-in风险

## 扩展指南

### 添加新Agent

1. 复制现有Agent目录结构
2. 实现 `agent.py` 主类
3. 定义专属工具集 (`tools/`)
4. 配置提示词模板 (`prompts/`)
5. 在 `app.py` 注册新Agent
6. 添加Streamlit调试界面

### 添加新搜索工具

```python
# <Agent>/tools/new_tool.py
class NewSearchTool:
    def __init__(self):
        pass

    def search(self, query: str) -> Dict:
        # 实现搜索逻辑
        return {"results": [...]}

# <Agent>/agent.py
from .tools.new_tool import NewSearchTool

class DeepSearchAgent:
    def __init__(self):
        self.new_tool = NewSearchTool()
```

### 添加新报告模板

在 `ReportEngine/report_template/` 创建 `.md` 文件,使用Markdown格式编写模板结构。Agent会自动检测并在合适场景选用。

## 注意事项

- **API调用限制**: 注意各LLM提供商的rate limit和token限制
- **数据库连接池**: 高并发场景需配置连接池参数
- **Playwright性能**: 爬虫系统占用资源较大,建议独立部署
- **日志轮转**: 生产环境需配置日志轮转防止磁盘占满
- **异常端口占用**: Streamlit进程异常退出可能占用端口,需手动kill
- **Git操作**: 项目无远程仓库,不要执行git push

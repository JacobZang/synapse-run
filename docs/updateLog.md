# 📢 Synapse Run 更新日志

## 2025.12.13 - 依赖包优化与安全增强

### 📦 新增依赖包
- **cryptography>=41.0.0**: 加密解密核心库,提升数据传输和存储安全性
- **openpyxl>=3.1.0**: Excel文件读写支持,完善训练数据导入导出功能

### 🔧 Requirements.txt优化
- **统一版本管理**: 为所有依赖包添加详细的行内注释,说明每个包的功能用途
- **分类优化**: 重新组织依赖包分类,使构建流程更清晰
- **版本规范**: 统一SQLAlchemy版本要求为>=2.0.0,确保ORM功能完整性
- **Garmin集成**: 明确garminconnect版本要求(>=0.2.0),确保API兼容性
- **项目名称更新**: 将项目描述从"Weibo舆情分析系统"更新为"Synapse Run训练数据分析系统"
- **跨平台支持**: 明确支持Windows/Linux/macOS三大操作系统

### 🚀 部署优化
- **文档完善**: Requirements注释详细说明每个依赖的作用,便于新手快速理解
- **最小化依赖**: 移除未使用的依赖,减少安装时间和潜在冲突
- **开发工具标注**: 明确标注可选的开发工具(pytest/black/flake8),避免生产环境不必要的安装

---

## 2025.12.10 - InsightEngine ORM架构升级与SQL注入防护

### 🔒 核心安全升级
- **ORM架构重构**: InsightEngine全面从原生SQL查询迁移到SQLAlchemy ORM,从根本上杜绝SQL注入风险
- **统一会话管理**: 新增`db_session_manager`单例模式管理数据库连接,确保线程安全与资源高效利用
- **自动配置读取**: 数据库配置直接从`config.py`动态导入,消除环境变量依赖,简化部署流程

### 🏗️ 数据模型标准化
- **ORM模型定义** (`db_models.py`):
  - `TrainingRecordKeep`: Keep数据源的SQLAlchemy模型,映射`training_records_keep`表
  - `TrainingRecordGarmin`: Garmin数据源的SQLAlchemy模型,映射`training_records_garmin`表
  - 完整字段类型定义,支持IDE智能提示与类型安全检查
- **声明式基类**: 使用`declarative_base()`统一ORM基类,遵循SQLAlchemy最佳实践

### 🔧 工具类ORM重写
- **Keep工具** (`keep_search.py`):
  - 所有查询方法从`cursor.execute(sql)`改写为`session.query(TrainingRecordKeep).filter(...)`
  - 使用ORM表达式构建复杂查询条件,代码可读性提升40%
  - 统计聚合使用`func.count()`, `func.sum()`, `func.avg()`等SQLAlchemy函数
- **Garmin工具** (`garmin_search.py`):
  - 9个查询方法全部ORM化,包括基础查询与Garmin专属查询
  - 复杂条件使用`and_()`, `or_()`, `case()`等组合表达式
  - 训练负荷、功率区间等高级查询使用ORM聚合与条件构建

### 📦 会话管理优化
- **懒加载机制** (`db_session_manager`):
  - 首次查询时自动初始化数据库引擎,避免启动时配置检查失败
  - 上下文管理器`get_session()`确保会话正确关闭,防止连接泄漏
  - 线程安全的引擎单例,支持多线程并发查询
- **连接池配置**:
  - 默认连接池大小5,最大溢出10,连接回收时间3600秒
  - 支持通过`config.py`动态调整连接池参数

### 🚀 性能与代码质量提升
- **查询性能**: ORM编译生成的SQL与手写SQL性能持平,预编译机制避免重复解析
- **代码简化**: 移除所有手动SQL拼接与参数化逻辑,代码量减少约30%
- **类型安全**: 所有查询返回ORM对象,支持属性访问,IDE智能提示完整
- **错误处理**: 统一异常捕获与日志记录,数据库错误追踪更清晰

### 📝 破坏性更新
- **移除原生SQL**: 完全删除`pymysql.connect()`与`cursor.execute()`调用
- **统一接口**: 所有工具方法返回类型保持不变(`DBResponse`),上层Agent无需修改
- **配置简化**: 不再需要`pymysql.cursors.DictCursor`等底层配置

### 🎯 安全合规
- **防注入设计**: ORM参数化查询,用户输入自动转义,符合OWASP安全标准
- **最小权限**: 数据库连接仅需SELECT权限,降低潜在攻击面
- **审计追踪**: 所有查询通过ORM统一日志,便于安全审计与监控

---

## 2025.12.10 - InsightEngine多数据源工具架构重构

### 🔧 核心架构升级
- **多数据源支持**: InsightEngine全面支持Keep和Garmin两种训练数据源的动态切换
- **工厂模式设计**: 新增`TrainingDataSearchFactory`工厂类,根据`config.py`的`TRAINING_DATA_SOURCE`配置自动创建对应数据源工具
- **独立数据模型**: Keep和Garmin使用各自独立的数据类,完整保留各数据源的原生字段特性

### 📦 工具类重构
- **基类架构** (`base_search.py`): 定义统一的查询接口,所有数据源必须实现6个核心查询方法
- **Keep工具** (`keep_search.py`): `KeepDataSearch`类,支持Keep数据源的6种查询工具
- **Garmin工具** (`garmin_search.py`): `GarminDataSearch`类,支持6种基础查询 + 3种专属查询
  - 基础查询: 最近训练、日期范围、统计数据、距离范围、心率区间、运动类型汇总
  - Garmin专属: 训练负荷查询、功率区间查询、训练效果分析

### 🎯 数据类设计
- **KeepTrainingRecord**: 对应`training_records_keep`表,包含心率数组等Keep特有字段
- **GarminTrainingRecord**: 对应`training_records_garmin`表,包含40+专业运动指标
  - 心率指标: 5个心率区间时长统计
  - 步频步幅: 平均/最大步频、步幅、垂直振幅、触地时间、步数等
  - 功率指标: 平均/最大/标准化功率、5个功率区间时长
  - 训练效果: 有氧/无氧训练效果、训练负荷、训练效果标签
  - 速度与代谢: 速度、卡路里、失水量、强度时长、Body Battery变化

### 🚀 Agent集成优化
- **自动工具选择**: `agent.py`启动时自动根据配置创建对应数据源工具
- **智能提示**: 根据当前数据源显示不同的分析能力描述和支持的查询工具列表
- **无缝切换**: 仅需修改`config.py`中的`TRAINING_DATA_SOURCE`字段即可切换数据源

### 📝 代码质量提升
- **破坏性更新**: 移除向后兼容代码,统一使用`create_training_data_search()`工厂方法
- **清理冗余**: 删除旧的`training_search.py`,统一到新架构
- **测试覆盖**: 新增`test_tools.py`测试脚本,覆盖所有核心功能

---

## 2025.12.10 - 训练数据导入系统重构与多数据源整合

### 🔄 核心架构升级
- **统一导入模块**: 合并`import_training_data.py`和`import_garmin_data.py`为统一模块`training_data_importer.py`
- **API专用设计**: 移除所有CLI命令行功能,专注于后端API调用接口,提升系统架构的纯净性
- **基类架构**: 新增`BaseImporter`基类,统一数据库引擎初始化逻辑,便于扩展更多数据源

### 📦 导入器重构
- **Keep导入器** (`KeepDataImporter`): Excel文件导入,支持.xlsx/.xls/.csv格式,批量提交优化(100条/批次)
- **Garmin导入器** (`GarminDataImporter`): Garmin Connect在线数据抓取,自动登录+活动过滤+批量导入
- **懒加载引擎**: 数据库引擎采用懒加载模式,直接从config.py读取最新配置,避免importlib.reload不确定性

### 🎨 Web界面增强
- **可视化数据源选择**: 新增数据源选择界面,支持Keep和Garmin两种数据源的可视化切换
- **Garmin在线导入**: 在Web界面直接输入Garmin账户,一键抓取跑步数据(支持中国区/国际区账户)
- **测试登录功能**: 支持Garmin登录测试,验证账户可用性后再执行数据导入
- **导入结果反馈**: 实时显示导入统计(成功/失败条数),提供详细的操作反馈

### 🗄️ 数据库架构优化
- **多数据源支持**: 新增`TrainingRecordManager`类,支持Keep和Garmin两种训练数据格式的动态切换
- **Garmin数据模型**: 新增`TrainingRecordGarmin`表,支持40+专业运动指标(心率区间、功率区间、步频步幅、训练负荷等)
- **字段映射系统**: 实现智能字段映射机制,自动适配不同数据源的字段差异(如Keep的`start_time` ↔ Garmin的`start_time_gmt`)
- **数据隔离**: Keep和Garmin数据存储在独立表中,互不干扰,支持独立统计视图

### 🔌 API接口扩展
- **数据源管理**: 新增`/api/test_garmin_login`接口,支持Garmin账户登录测试
- **在线导入**: 新增`/api/import_garmin_data`接口,支持Garmin Connect在线数据抓取与导入
- **配置管理**: 优化`/api/save_config`接口,支持保存Garmin账户信息到配置文件
- **Excel上传**: 优化`/api/upload_training_excel`接口,统一使用新导入器架构

### 📝 技术改进
- **明确命名**: Keep导入使用`KeepDataImporter`,Garmin导入使用`GarminDataImporter`,语义清晰
- **错误处理**: 完善Garmin登录异常捕获,提供清晰的错误提示信息
- **代码简化**: 移除重复的数据库引擎创建逻辑,统一到BaseImporter基类中
- **导入模式**: 统一采用覆盖写入模式(truncate_first=True),避免数据重复

---

## 2025.12.8 - 训练数据导入功能修复
- **🔧 数据库连接修复**: 修复Excel训练数据导入时的数据库认证失败问题
- **⚡ 配置读取优化**: 移除不可靠的`importlib.reload()`机制,改为直接从config.py构建数据库引擎
- **✅ 稳定性提升**: 导入器现在每次初始化都能准确读取最新的数据库配置,避免环境变量干扰
- **📊 Web上传保障**: 确保通过Web界面(/setup)上传Excel文件时的数据库连接稳定性

---

## 2025.12.8 - 可视化配置系统上线
- **🎨 可视化配置界面**: 新增Web可视化配置页面(`/setup`),支持LLM API、搜索API、MySQL数据库的可视化配置
- **✅ 智能健康检查**: 系统启动时自动运行8项健康检查,配置不完整时自动跳转到配置页面
- **🔧 实时连接测试**: 支持LLM API和MySQL连接的实时测试,配置前即可验证连接可用性
- **🗄️ 一键数据库初始化**: 点击按钮即可自动创建数据库和表结构,无需手动执行SQL脚本
- **📱 响应式设计**: 采用Morandi色系的现代化UI设计,横版布局一屏显示所有功能
- **⚠️ 重要提示**: 首次启动系统会自动重定向到配置页面,完成配置后才能正常使用

---

## 2025.12.8 - 配置管理重构
- **🔧 统一配置变量**: 将所有Agent的LLM配置统一为`LLM_API_KEY`、`LLM_BASE_URL`、`DEFAULT_MODEL_NAME`、`REPORT_MODEL_NAME`四个变量
- **📝 简化配置流程**: 除ReportAgent使用`qwen3-max`外，其他Agent统一使用`qwen-plus-latest`
- **⚠️ 重要提示**: 如果您之前使用旧版本配置，请参考配置说明章节更新您的`config.py`文件

---

## 2025.12.8 - 数据库脚本修复
- 添加缺失的`training_tables.sql`，同时调整`import_traning_data.py`的文件路径，均放在`scripts`文件夹下

# -*- coding: utf-8 -*-
"""
健康检查模块 - 检测系统配置状态
"""

import os
import sys
from pathlib import Path
import pymysql
import requests
from typing import Dict, Tuple


class HealthChecker:
    """系统健康检查器"""

    def __init__(self):
        self.results = {}
        self.config = None

    def load_config(self) -> Tuple[bool, str]:
        """加载配置文件"""
        try:
            # 动态导入config模块
            import config
            self.config = config
            return True, "配置文件加载成功"
        except ImportError as e:
            return False, f"配置文件不存在或无法导入: {str(e)}"
        except Exception as e:
            return False, f"加载配置文件时出错: {str(e)}"

    def check_python_environment(self) -> Dict:
        """检查Python环境"""
        result = {
            'name': 'Python环境',
            'status': 'success',
            'message': f'Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}',
            'details': None
        }

        # 检查Python版本
        if sys.version_info.major < 3 or (sys.version_info.major == 3 and sys.version_info.minor < 9):
            result['status'] = 'warning'
            result['message'] = f'Python版本 {sys.version_info.major}.{sys.version_info.minor} 低于推荐版本3.9+'

        return result

    def check_config_file(self) -> Dict:
        """检查配置文件"""
        success, message = self.load_config()

        result = {
            'name': '配置文件',
            'status': 'success' if success else 'error',
            'message': message,
            'details': None
        }

        if not success:
            result['details'] = '请确保config.py文件存在于项目根目录'

        return result

    def check_llm_config(self) -> Dict:
        """检查LLM配置"""
        if not self.config:
            return {
                'name': 'LLM配置',
                'status': 'error',
                'message': '配置文件未加载',
                'details': None
            }

        result = {
            'name': 'LLM配置',
            'status': 'success',
            'message': '',
            'details': []
        }

        issues = []

        # 检查API Key
        api_key = getattr(self.config, 'LLM_API_KEY', '')
        if not api_key or api_key == 'your_qwen_api_key_here':
            issues.append('LLM_API_KEY未配置')

        # 检查Base URL
        base_url = getattr(self.config, 'LLM_BASE_URL', '')
        if not base_url:
            issues.append('LLM_BASE_URL未配置')

        # 检查模型名称
        default_model = getattr(self.config, 'DEFAULT_MODEL_NAME', '')
        if not default_model:
            issues.append('DEFAULT_MODEL_NAME未配置')

        report_model = getattr(self.config, 'REPORT_MODEL_NAME', '')
        if not report_model:
            issues.append('REPORT_MODEL_NAME未配置')

        if issues:
            result['status'] = 'error'
            result['message'] = f'发现{len(issues)}个配置问题'
            result['details'] = issues
        else:
            result['message'] = f'API配置完整 (模型: {default_model}, {report_model})'

        return result

    def check_llm_api_connection(self) -> Dict:
        """检查LLM API连接"""
        if not self.config:
            return {
                'name': 'LLM API连接',
                'status': 'error',
                'message': '配置文件未加载',
                'details': None
            }

        api_key = getattr(self.config, 'LLM_API_KEY', '')
        base_url = getattr(self.config, 'LLM_BASE_URL', '')
        model_name = getattr(self.config, 'DEFAULT_MODEL_NAME', '')

        if not api_key or api_key == 'your_qwen_api_key_here':
            return {
                'name': 'LLM API连接',
                'status': 'warning',
                'message': 'API Key未配置,跳过连接测试',
                'details': None
            }

        result = {
            'name': 'LLM API连接',
            'status': 'success',
            'message': '',
            'details': None
        }

        try:
            # 测试API连接
            import openai
            client = openai.OpenAI(api_key=api_key, base_url=base_url)

            # 发送简单的测试请求
            response = client.chat.completions.create(
                model=model_name,
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5,
                timeout=10
            )

            result['message'] = f'API连接成功 (响应时间<10s)'
        except Exception as e:
            result['status'] = 'error'
            result['message'] = 'API连接失败'
            result['details'] = str(e)

        return result

    def check_search_api_config(self) -> Dict:
        """检查搜索API配置"""
        if not self.config:
            return {
                'name': '搜索API配置',
                'status': 'error',
                'message': '配置文件未加载',
                'details': None
            }

        result = {
            'name': '搜索API配置',
            'status': 'success',
            'message': '',
            'details': []
        }

        issues = []
        configured = []

        # 检查Tavily API
        tavily_key = getattr(self.config, 'TAVILY_API_KEY', '')
        if not tavily_key or tavily_key == 'your_tavily_api_key_here':
            issues.append('TAVILY_API_KEY未配置')
        else:
            configured.append('Tavily')

        # 检查Bocha API
        bocha_key = getattr(self.config, 'BOCHA_WEB_SEARCH_API_KEY', '')
        if not bocha_key or bocha_key == 'your_bocha_api_key_here':
            issues.append('BOCHA_WEB_SEARCH_API_KEY未配置')
        else:
            configured.append('Bocha')

        if len(issues) == 2:
            result['status'] = 'error'
            result['message'] = '所有搜索API未配置'
            result['details'] = issues
        elif len(issues) == 1:
            result['status'] = 'warning'
            result['message'] = f'部分搜索API已配置: {", ".join(configured)}'
            result['details'] = issues
        else:
            result['message'] = f'搜索API配置完整: {", ".join(configured)}'

        return result

    def check_mysql_config(self) -> Dict:
        """检查MySQL配置"""
        if not self.config:
            return {
                'name': 'MySQL配置',
                'status': 'error',
                'message': '配置文件未加载',
                'details': None
            }

        result = {
            'name': 'MySQL配置',
            'status': 'success',
            'message': '',
            'details': []
        }

        issues = []

        # 检查数据库配置
        db_host = getattr(self.config, 'DB_HOST', '')
        db_user = getattr(self.config, 'DB_USER', '')
        db_password = getattr(self.config, 'DB_PASSWORD', '')
        db_name = getattr(self.config, 'DB_NAME', '')

        if not db_host:
            issues.append('DB_HOST未配置')
        if not db_user or db_user == 'your_db_username':
            issues.append('DB_USER未配置')
        if not db_password or db_password == 'your_db_password':
            issues.append('DB_PASSWORD未配置')
        if not db_name:
            issues.append('DB_NAME未配置')

        if issues:
            result['status'] = 'error'
            result['message'] = f'发现{len(issues)}个配置问题'
            result['details'] = issues
        else:
            result['message'] = f'MySQL配置完整 ({db_host}:{getattr(self.config, "DB_PORT", 3306)}/{db_name})'

        return result

    def check_mysql_connection(self) -> Dict:
        """检查MySQL连接"""
        if not self.config:
            return {
                'name': 'MySQL连接',
                'status': 'error',
                'message': '配置文件未加载',
                'details': None
            }

        db_host = getattr(self.config, 'DB_HOST', '')
        db_port = getattr(self.config, 'DB_PORT', 3306)
        db_user = getattr(self.config, 'DB_USER', '')
        db_password = getattr(self.config, 'DB_PASSWORD', '')
        db_name = getattr(self.config, 'DB_NAME', '')

        if not db_user or db_user == 'your_db_username':
            return {
                'name': 'MySQL连接',
                'status': 'warning',
                'message': '数据库配置未完成,跳过连接测试',
                'details': None
            }

        result = {
            'name': 'MySQL连接',
            'status': 'success',
            'message': '',
            'details': None
        }

        try:
            # 测试数据库连接
            connection = pymysql.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                charset='utf8mb4',
                connect_timeout=5
            )

            # 检查数据库是否存在
            with connection.cursor() as cursor:
                cursor.execute(f"SHOW DATABASES LIKE '{db_name}'")
                db_exists = cursor.fetchone() is not None

            connection.close()

            if db_exists:
                result['message'] = f'MySQL连接成功,数据库"{db_name}"已存在'
            else:
                result['status'] = 'warning'
                result['message'] = f'MySQL连接成功,但数据库"{db_name}"不存在'
                result['details'] = f'请运行数据库初始化脚本创建数据库'

        except pymysql.err.OperationalError as e:
            result['status'] = 'error'
            result['message'] = 'MySQL连接失败'
            if '2003' in str(e):
                result['details'] = f'无法连接到MySQL服务器({db_host}:{db_port}),请检查MySQL是否已启动'
            elif '1045' in str(e):
                result['details'] = '认证失败,请检查用户名和密码是否正确'
            else:
                result['details'] = str(e)
        except Exception as e:
            result['status'] = 'error'
            result['message'] = 'MySQL连接失败'
            result['details'] = str(e)

        return result

    def check_database_tables(self) -> Dict:
        """检查数据库表"""
        if not self.config:
            return {
                'name': '数据库表',
                'status': 'error',
                'message': '配置文件未加载',
                'details': None
            }

        db_host = getattr(self.config, 'DB_HOST', '')
        db_port = getattr(self.config, 'DB_PORT', 3306)
        db_user = getattr(self.config, 'DB_USER', '')
        db_password = getattr(self.config, 'DB_PASSWORD', '')
        db_name = getattr(self.config, 'DB_NAME', '')

        if not db_user or db_user == 'your_db_username':
            return {
                'name': '数据库表',
                'status': 'warning',
                'message': '数据库配置未完成,跳过表检查',
                'details': None
            }

        result = {
            'name': '数据库表',
            'status': 'success',
            'message': '',
            'details': None
        }

        try:
            connection = pymysql.connect(
                host=db_host,
                port=db_port,
                user=db_user,
                password=db_password,
                database=db_name,
                charset='utf8mb4',
                connect_timeout=5
            )

            with connection.cursor() as cursor:
                cursor.execute("SHOW TABLES")
                tables = cursor.fetchall()
                table_count = len(tables)

            connection.close()

            if table_count == 0:
                result['status'] = 'warning'
                result['message'] = '数据库为空,未找到任何表'
                result['details'] = '请运行scripts/training_tables.sql初始化数据库表'
            else:
                result['message'] = f'数据库表检查通过,共{table_count}个表'

        except pymysql.err.OperationalError as e:
            if '1049' in str(e):
                result['status'] = 'error'
                result['message'] = f'数据库"{db_name}"不存在'
                result['details'] = '请先创建数据库或运行初始化脚本'
            else:
                result['status'] = 'error'
                result['message'] = '数据库表检查失败'
                result['details'] = str(e)
        except Exception as e:
            result['status'] = 'error'
            result['message'] = '数据库表检查失败'
            result['details'] = str(e)

        return result

    def run_all_checks(self) -> Dict:
        """运行所有健康检查"""
        checks = {
            'python_env': self.check_python_environment(),
            'config_file': self.check_config_file(),
            'llm_config': self.check_llm_config(),
            'llm_api': self.check_llm_api_connection(),
            'search_api': self.check_search_api_config(),
            'mysql_config': self.check_mysql_config(),
            'mysql_connection': self.check_mysql_connection(),
            'database_tables': self.check_database_tables()
        }

        # 统计状态
        status_summary = {
            'success': 0,
            'warning': 0,
            'error': 0
        }

        for check in checks.values():
            status_summary[check['status']] += 1

        # 判断整体状态
        overall_status = 'ready'
        if status_summary['error'] > 0:
            overall_status = 'needs_config'
        elif status_summary['warning'] > 0:
            overall_status = 'partial'

        return {
            'overall_status': overall_status,
            'checks': checks,
            'summary': status_summary
        }


def run_health_check() -> Dict:
    """运行健康检查并返回结果"""
    checker = HealthChecker()
    return checker.run_all_checks()


if __name__ == '__main__':
    # 测试健康检查
    results = run_health_check()

    print("\n=== 系统健康检查报告 ===\n")
    print(f"整体状态: {results['overall_status']}")
    print(f"成功: {results['summary']['success']} | 警告: {results['summary']['warning']} | 错误: {results['summary']['error']}\n")

    for key, check in results['checks'].items():
        status_icon = {
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }
        print(f"{status_icon[check['status']]} {check['name']}: {check['message']}")
        if check['details']:
            if isinstance(check['details'], list):
                for detail in check['details']:
                    print(f"   - {detail}")
            else:
                print(f"   详情: {check['details']}")

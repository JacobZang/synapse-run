"""
中长跑理论搜索工具 (Tavily)

版本: 2.1
最后更新: 2025-12-06

简化版本,专注于中长跑运动科学理论搜索,无需考虑时间范围等复杂参数。

提供单一核心工具:
- deep_search_news: 对中长跑理论主题进行最全面的深度分析

更新日志:
- v2.1: 添加学术白名单域名过滤和查询增强功能
"""

import os
import sys
from typing import List, Dict, Any, Optional

# 添加utils目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
utils_dir = os.path.join(root_dir, 'utils')
if utils_dir not in sys.path:
    sys.path.append(utils_dir)

from retry_helper import with_graceful_retry, SEARCH_API_RETRY_CONFIG
from dataclasses import dataclass, field

# 运行前请确保已安装Tavily库: pip install tavily-python
try:
    from tavily import TavilyClient
except ImportError:
    raise ImportError("Tavily库未安装,请运行 `pip install tavily-python` 进行安装。")


# --- 中长跑运动科学专家 - Tavily 白名单 ---

RUNNING_SCIENCE_WHITELIST = [
    # --- 学术与医学 ---
    "ncbi.nlm.nih.gov",
    "pubmed.ncbi.nlm.nih.gov",
    "researchgate.net",
    "journals.lww.com",
    "frontiersin.org",
    "sciencedirect.com",
    "wiley.com",
    "springer.com",
    "tandfonline.com",

    # --- 顶级训练理论与科学博客 ---
    "scienceofrunning.com",   # Steve Magness - 运动科学研究
    "trainingpeaks.com",      # 科学化训练平台
    "outsideonline.com",      # 包含 Sweat Science 专栏
    "mariusbakken.com",       # 挪威流派/乳酸阈值训练
    "fellrnr.com",            # 极客跑者的维基百科,数据详实
    "mysportscience.com",     # Asker Jeukendrup - 运动营养学权威
    "runnersconnect.net",     # 训练科学与损伤预防
    "strengthrunning.com",    # 力量训练与跑步结合

    # --- 权威垂直媒体 ---
    "runnersworld.com",       # 跑者世界
    "letsrun.com",            # 精英跑者社区
    "worldathletics.org",     # 世界田联官方
    "podiumrunner.com",       # 前 Competitor Running
    "runningmagazine.ca",     # 加拿大跑步杂志
    "irunfar.com",            # 越野跑科学

    # --- 运动生理与医学 ---
    "sportsci.org",           # 运动科学研究网
    "gssiweb.org",            # 佳得乐运动科学研究所
    "acsm.org",               # 美国运动医学会
    "nsca.com",               # 美国力量与体能协会

    # --- 优质中文源 ---
    "98pao.com",              # 98跑 - 中文跑步社区
    "iranshao.com",           # 爱燃烧 - 跑步装备与训练
    "sodichan.com",           # 速度耐力 - 部分专业内容
    "runningbiji.com",        # 跑步笔记
]


# --- 内容过滤黑名单 (防止敏感内容) ---

CONTENT_BLACKLIST_KEYWORDS = [
    # 成人内容关键词
    "porn", "sex", "xxx", "adult", "nude", "裸", "色情", "成人",
    # 赌博相关
    "casino", "gambling", "赌博", "博彩",
    # 其他敏感内容
    "dating", "约会", "交友",
]

# 可疑域名黑名单 (已知的非学术站点)
DOMAIN_BLACKLIST = [
    "xvideos.com", "pornhub.com", "redtube.com",  # 成人网站
    "bet365.com", "888casino.com",  # 赌博网站
    # 可以继续添加发现的问题域名
]


# --- 学术查询增强关键词库 ---

ACADEMIC_ENHANCEMENT_KEYWORDS = {
    # 生理学相关
    "physiology": ["VO2max", "lactate threshold", "aerobic capacity", "anaerobic threshold", "oxygen uptake"],
    "training": ["training protocol", "periodization", "training adaptation", "training load", "progressive overload"],
    "endurance": ["endurance performance", "aerobic metabolism", "mitochondrial adaptation", "capillary density"],
    "injury": ["biomechanics", "injury prevention", "musculoskeletal", "gait analysis", "running mechanics"],
    "nutrition": ["carbohydrate loading", "glycogen storage", "hydration strategy", "electrolyte balance", "energy metabolism"],
    "recovery": ["recovery protocol", "supercompensation", "DOMS", "muscle regeneration", "adaptive response"],
    "performance": ["performance optimization", "race strategy", "pacing", "fatigue resistance", "running economy"],
    "strength": ["strength training", "plyometrics", "core stability", "neuromuscular adaptation", "power output"],
}


def is_content_safe(text: str, url: str = "") -> bool:
    """
    检查内容是否安全(不包含敏感信息)

    Args:
        text: 要检查的文本内容
        url: URL地址

    Returns:
        True表示安全,False表示包含敏感内容
    """
    if not text:
        return True

    # 检查URL黑名单
    if url:
        for blacklisted_domain in DOMAIN_BLACKLIST:
            if blacklisted_domain in url.lower():
                return False

    # 检查内容关键词黑名单
    text_lower = text.lower()
    for keyword in CONTENT_BLACKLIST_KEYWORDS:
        if keyword in text_lower:
            return False

    return True


def enhance_query_for_academic_search(original_query: str) -> str:
    """
    增强搜索查询,强制搜索引擎进入"学术模式"

    策略:
    1. 检测查询中的主题类别
    2. 添加相关的英文学术术语
    3. 添加通用的学术关键词(study, research, protocol等)
    4. 添加排除敏感内容的关键词

    Args:
        original_query: 原始用户查询

    Returns:
        增强后的查询字符串
    """
    query_lower = original_query.lower()

    # 收集匹配的学术关键词
    matched_keywords = []
    for category, keywords in ACADEMIC_ENHANCEMENT_KEYWORDS.items():
        if category in query_lower or any(kw.lower() in query_lower for kw in keywords):
            # 从每个匹配类别选择2-3个最相关的术语
            matched_keywords.extend(keywords[:2])

    # 通用学术增强词(总是添加)
    base_academic_terms = ["training", "performance", "physiology", "research"]

    # 如果没有匹配到特定类别,使用通用增强
    if not matched_keywords:
        matched_keywords = ["VO2max", "lactate threshold", "training adaptation"]

    # 合并:原查询 + 匹配的术语 + 基础术语
    all_terms = matched_keywords[:3] + base_academic_terms[:2]
    enhanced_query = f"{original_query} {' '.join(all_terms)}"

    # 添加排除敏感内容的操作符(Google搜索语法)
    enhanced_query += " -porn -sex -adult -casino -gambling"

    return enhanced_query

# --- 1. 数据结构定义 ---

@dataclass
class SearchResult:
    """网页搜索结果数据类"""
    title: str
    url: str
    content: str
    score: Optional[float] = None
    raw_content: Optional[str] = None
    published_date: Optional[str] = None

@dataclass
class ImageResult:
    """图片搜索结果数据类"""
    url: str
    description: Optional[str] = None

@dataclass
class TavilyResponse:
    """封装Tavily API的完整返回结果"""
    query: str
    answer: Optional[str] = None
    results: List[SearchResult] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    response_time: Optional[float] = None


# --- 2. 核心客户端与搜索工具 ---

class TavilyNewsAgency:
    """
    中长跑理论搜索客户端
    提供单一的深度搜索工具,专注于理论研究
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        初始化客户端
        Args:
            api_key: Tavily API密钥,若不提供则从环境变量 TAVILY_API_KEY 读取
        """
        if api_key is None:
            api_key = os.getenv("TAVILY_API_KEY")
            if not api_key:
                raise ValueError("Tavily API Key未找到!请设置TAVILY_API_KEY环境变量或在初始化时提供")
        self._client = TavilyClient(api_key=api_key)

    @with_graceful_retry(SEARCH_API_RETRY_CONFIG, default_return=TavilyResponse(query="搜索失败"))
    def _search_internal(self, **kwargs) -> TavilyResponse:
        """内部通用的搜索执行器,包含内容安全过滤"""
        try:
            kwargs['topic'] = 'general'
            api_params = {k: v for k, v in kwargs.items() if v is not None}
            response_dict = self._client.search(**api_params)

            # 过滤掉不安全的搜索结果
            filtered_results = []
            blocked_count = 0

            for item in response_dict.get('results', []):
                url = item.get('url', '')
                title = item.get('title', '')
                content = item.get('content', '')

                # 检查URL、标题和内容是否安全
                if (is_content_safe(title, url) and
                    is_content_safe(content, url)):
                    filtered_results.append(
                        SearchResult(
                            title=title,
                            url=url,
                            content=content,
                            score=item.get('score'),
                            raw_content=item.get('raw_content'),
                            published_date=item.get('published_date')
                        )
                    )
                else:
                    blocked_count += 1
                    print(f"⚠️ 已过滤不安全内容: {url}")

            if blocked_count > 0:
                print(f"✅ 内容过滤: 已拦截 {blocked_count} 条潜在敏感内容")

            # 图片结果也进行过滤
            image_results = []
            for item in response_dict.get('images', []):
                url = item.get('url', '')
                desc = item.get('description', '')
                if is_content_safe(desc, url):
                    image_results.append(ImageResult(url=url, description=desc))

            return TavilyResponse(
                query=response_dict.get('query'),
                answer=response_dict.get('answer'),
                results=filtered_results,
                images=image_results,
                response_time=response_dict.get('response_time')
            )
        except Exception as e:
            print(f"搜索时发生错误: {str(e)}")
            raise e  # 让重试机制捕获并处理

    # --- Agent 可用的工具方法 ---

    def deep_search_news(self, query: str, enable_query_enhancement: bool = True,
                        use_whitelist: bool = True) -> TavilyResponse:
        """
        【工具】深度理论搜索: 对中长跑理论主题进行最全面、最深入的搜索

        返回AI生成的详细摘要答案和最多20条最相关的搜索结果。
        适用于需要全面了解中长跑训练理论、运动科学原理的场景。

        安全保护机制:
        1. 白名单域名优先(30+权威学术和专业网站)
        2. 搜索查询添加排除敏感内容操作符
        3. 结果多层过滤:URL黑名单 + 内容关键词检测
        4. 自动拦截并记录被过滤的不安全内容

        Args:
            query: 搜索查询,建议使用中长跑专业术语
            enable_query_enhancement: 是否启用学术查询增强(默认True)
            use_whitelist: 是否使用学术白名单过滤域名(默认True)

        Returns:
            TavilyResponse对象,包含经过安全过滤的搜索结果和AI摘要
        """
        # 查询增强
        if enable_query_enhancement:
            enhanced_query = enhance_query_for_academic_search(query)
            print(f"--- TOOL: 深度理论搜索 ---")
            print(f"原始查询: {query}")
            print(f"增强查询: {enhanced_query}")
        else:
            enhanced_query = query
            print(f"--- TOOL: 深度理论搜索 (query: {query}) ---")

        # 构建搜索参数
        search_params = {
            "query": enhanced_query,
            "search_depth": "advanced",
            "max_results": 20,
            "include_answer": "advanced"
        }

        # 添加白名单
        if use_whitelist:
            search_params["include_domains"] = RUNNING_SCIENCE_WHITELIST
            print(f"已启用学术白名单过滤 ({len(RUNNING_SCIENCE_WHITELIST)} 个权威域名)")

        return self._search_internal(**search_params)


# --- 3. 测试与使用示例 ---

def print_response_summary(response: TavilyResponse):
    """简化的打印函数,用于展示测试结果"""
    if not response or not response.query:
        print("未能获取有效响应。")
        return

    print(f"\n查询: '{response.query}' | 耗时: {response.response_time}s")
    if response.answer:
        print(f"AI摘要: {response.answer[:120]}...")
    print(f"找到 {len(response.results)} 条网页, {len(response.images)} 张图片。")
    if response.results:
        first_result = response.results[0]
        date_info = f"(发布于: {first_result.published_date})" if first_result.published_date else ""
        print(f"第一条结果: {first_result.title} {date_info}")
    print("-" * 60)


if __name__ == "__main__":
    # 在运行前,请确保您已设置 TAVILY_API_KEY 环境变量

    try:
        # 初始化客户端
        agency = TavilyNewsAgency()

        print("=" * 80)
        print("测试1: 标准搜索(查询增强 + 白名单)")
        print("=" * 80)
        response = agency.deep_search_news(
            query="马拉松训练Lydiard体系理论",
            enable_query_enhancement=True,
            use_whitelist=True
        )
        print_response_summary(response)

        print("\n" + "=" * 80)
        print("测试2: 仅查询增强,不使用白名单")
        print("=" * 80)
        response = agency.deep_search_news(
            query="间歇训练对VO2max的影响",
            enable_query_enhancement=True,
            use_whitelist=False
        )
        print_response_summary(response)

        print("\n" + "=" * 80)
        print("测试3: 原始查询,不做任何增强")
        print("=" * 80)
        response = agency.deep_search_news(
            query="跑步损伤预防",
            enable_query_enhancement=False,
            use_whitelist=False
        )
        print_response_summary(response)

    except ValueError as e:
        print(f"初始化失败: {e}")
        print("请确保 TAVILY_API_KEY 环境变量已正确设置。")
    except Exception as e:
        print(f"测试过程中发生未知错误: {e}")

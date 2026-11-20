#!/usr/bin/env python3
"""Web research adapter for amazon-a-plus-graph.

Inputs:
  - product name, optional brand/target site, optional custom queries or seed URLs
  - one of Tavily, Brave Search, Firecrawl, or requests-only seed URL scraping
Output:
  - research.json compatible with build_long_detail.py

This script does not use an LLM. It gathers sources, extracts conservative
candidate facts, and marks them for agent review before image prompts use them.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

try:
    import requests
except ImportError:
    print("[ERROR] 缺少 requests，请先执行: python -m pip install requests", file=sys.stderr)
    sys.exit(1)


DEFAULT_RISK_NOTES = [
    "不要写价格、优惠、限时、满减、下单、包邮、售后、保证等平台敏感或促销话术。",
    "不要写No.1、最好、顶级、最健康、治疗、减脂、控糖、增强免疫等绝对化或健康功效表述。",
    "认证、奖项、产地、检测数据、营养数字、销量排名、对比结论必须由用户输入或权威来源支持后再入图。",
    "搜索结果是候选资料；Agent必须复核来源可信度和当前SKU适用性，再把事实用于画面文案。",
]

DEFAULT_MISSING_FACTS = [
    "当前SKU的完整包装高清图",
    "当前SKU对应的认证编号、生产批次、产地或型号信息",
    "目标站点的正式商品标题和合规要求",
]

FACT_KEYWORDS = [
    "官方",
    "品牌",
    "有机",
    "认证",
    "规格",
    "净含量",
    "配料",
    "成分",
    "营养",
    "产地",
    "奶源",
    "牧场",
    "沙漠",
    "绿洲",
    "京东",
    "旗舰店",
    "标准",
    "保质期",
    "储存",
    "包装",
    "型号",
    "参数",
    "技术",
    "功能",
]


@dataclass
class SourceResult:
    title: str
    url: str
    snippet: str = ""
    content: str = ""
    query: str = ""
    provider: str = ""
    score: float | None = None
    source_type: str = "web"


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.skip_depth = 0
        self.title = ""
        self._in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style", "noscript", "svg"}:
            self.skip_depth += 1
        if tag == "title":
            self._in_title = True
        if tag in {"p", "br", "li", "h1", "h2", "h3", "tr"}:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript", "svg"} and self.skip_depth:
            self.skip_depth -= 1
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        text = normalize_space(data)
        if not text:
            return
        if self._in_title:
            self.title += text
        self.parts.append(text)

    def text(self) -> str:
        return normalize_space("\n".join(self.parts))


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def truncate(text: str, limit: int) -> str:
    text = normalize_space(text)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def find_env_file(start: Path | None = None) -> Path | None:
    current = (start or Path(__file__).resolve()).parent
    for _ in range(8):
        candidate = current / ".env"
        if candidate.exists():
            return candidate
        if current.parent == current:
            break
        current = current.parent
    return None


def load_env(env_file: str | None) -> None:
    target = Path(env_file) if env_file else find_env_file()
    if not target or not target.exists():
        return
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def request_json(
    method: str,
    url: str,
    *,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    payload: dict[str, Any] | None = None,
    timeout: int = 45,
) -> dict[str, Any]:
    response = requests.request(method, url, headers=headers, params=params, json=payload, timeout=timeout)
    try:
        data = response.json()
    except ValueError as exc:
        raise RuntimeError(f"非 JSON 响应: HTTP {response.status_code}: {truncate(response.text, 300)}") from exc
    if response.status_code >= 400:
        raise RuntimeError(f"HTTP {response.status_code}: {json.dumps(data, ensure_ascii=False)[:800]}")
    return data


def default_queries(product_name: str, brand: str, target_site: str) -> list[str]:
    base = product_name.strip()
    brand_prefix = f"{brand} " if brand and brand not in base else ""
    queries = [
        f"{brand_prefix}{base} 官方 规格",
        f"{brand_prefix}{base} 品牌故事 官方",
        f"{base} 配料 营养成分 认证",
    ]
    if target_site:
        queries.append(f"{base} {target_site} 商品")
    return queries


def apply_domain_filters(queries: list[str], domains: list[str]) -> list[str]:
    if not domains:
        return queries
    scoped = []
    suffix = " ".join(f"site:{domain}" for domain in domains)
    for query in queries:
        scoped.append(f"{query} {suffix}")
    return scoped


def search_tavily(query: str, args: argparse.Namespace) -> list[SourceResult]:
    api_key = os.getenv("TAVILY_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未找到 TAVILY_API_KEY")
    endpoint = args.tavily_api_url.rstrip("/") + "/search"
    payload: dict[str, Any] = {
        "query": query,
        "search_depth": args.search_depth,
        "max_results": args.max_results,
        "include_answer": False,
        "include_images": False,
    }
    if args.tavily_include_raw_content != "none":
        payload["include_raw_content"] = args.tavily_include_raw_content
    try:
        data = request_json(
            "POST",
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload=payload,
            timeout=args.timeout,
        )
    except RuntimeError:
        if "include_raw_content" not in payload:
            raise
        payload.pop("include_raw_content", None)
        data = request_json(
            "POST",
            endpoint,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload=payload,
            timeout=args.timeout,
        )
    results = []
    for item in data.get("results", []) or []:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        results.append(
            SourceResult(
                title=normalize_space(item.get("title", "")),
                url=item["url"],
                snippet=normalize_space(item.get("content", "")),
                content=normalize_space(item.get("raw_content", "")),
                query=query,
                provider="tavily",
                score=item.get("score"),
            )
        )
    return results


def search_brave(query: str, args: argparse.Namespace) -> list[SourceResult]:
    api_key = (os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("BRAVE_API_KEY") or "").strip()
    if not api_key:
        raise RuntimeError("未找到 BRAVE_SEARCH_API_KEY 或 BRAVE_API_KEY")
    data = request_json(
        "GET",
        args.brave_api_url,
        headers={
            "X-Subscription-Token": api_key,
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
        },
        params={"q": query, "count": args.max_results, "text_decorations": False},
        timeout=args.timeout,
    )
    web = data.get("web", {}) if isinstance(data, dict) else {}
    results = []
    for item in web.get("results", []) or []:
        if not isinstance(item, dict) or not item.get("url"):
            continue
        results.append(
            SourceResult(
                title=normalize_space(item.get("title", "")),
                url=item["url"],
                snippet=normalize_space(item.get("description", "")),
                query=query,
                provider="brave",
            )
        )
    return results


def scrape_firecrawl(url: str, args: argparse.Namespace) -> SourceResult:
    api_key = os.getenv("FIRECRAWL_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("未找到 FIRECRAWL_API_KEY")
    data = request_json(
        "POST",
        args.firecrawl_api_url.rstrip("/") + "/scrape",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload={"url": url, "formats": ["markdown"], "onlyMainContent": True},
        timeout=args.timeout,
    )
    body = data.get("data", data)
    metadata = body.get("metadata", {}) if isinstance(body, dict) else {}
    content = ""
    if isinstance(body, dict):
        content = body.get("markdown") or body.get("content") or body.get("text") or ""
    return SourceResult(
        title=normalize_space(metadata.get("title", "")) or url,
        url=url,
        content=normalize_space(content),
        provider="firecrawl",
        source_type="scrape",
    )


def scrape_requests(url: str, args: argparse.Namespace) -> SourceResult:
    response = requests.get(url, headers={"User-Agent": args.user_agent}, timeout=args.timeout)
    response.raise_for_status()
    if response.apparent_encoding:
        response.encoding = response.apparent_encoding
    parser = TextExtractor()
    parser.feed(response.text)
    title = normalize_space(parser.title) or url
    return SourceResult(
        title=title,
        url=url,
        content=parser.text(),
        provider="requests",
        source_type="scrape",
    )


def choose_provider(args: argparse.Namespace) -> str:
    if args.provider != "auto":
        return args.provider
    if os.getenv("TAVILY_API_KEY"):
        return "tavily"
    if os.getenv("BRAVE_SEARCH_API_KEY") or os.getenv("BRAVE_API_KEY"):
        return "brave"
    if os.getenv("FIRECRAWL_API_KEY") and args.seed_url:
        return "firecrawl"
    if args.seed_url:
        return "requests"
    raise RuntimeError(
        "未找到可用联网研究 provider。请设置 TAVILY_API_KEY / BRAVE_SEARCH_API_KEY，"
        "或提供 --seed-url 并使用 --provider requests/firecrawl。"
    )


def dedupe_sources(sources: list[SourceResult]) -> list[SourceResult]:
    seen: set[str] = set()
    deduped = []
    for source in sources:
        key = source.url
        if key in seen:
            continue
        seen.add(key)
        deduped.append(source)
    return deduped


def split_sentences(text: str) -> list[str]:
    cleaned = normalize_space(text)
    if not cleaned:
        return []
    pieces = re.split(r"(?<=[。！？!?；;])|(?<=\.)\s+", cleaned)
    return [normalize_space(item) for item in pieces if normalize_space(item)]


def host_score(url: str, preferred_domains: list[str]) -> int:
    host = urlparse(url).netloc.lower()
    if not host:
        return 0
    score = 0
    if any(domain.lower() in host for domain in preferred_domains):
        score += 4
    if any(token in host for token in ["official", "gov", "edu"]):
        score += 2
    if host.endswith(".gov.cn") or host.endswith(".gov"):
        score += 3
    return score


def extract_candidate_facts(
    sources: list[SourceResult],
    *,
    product_name: str,
    brand: str,
    preferred_domains: list[str],
    max_facts: int,
) -> list[dict[str, Any]]:
    product_tokens = [token for token in re.split(r"[\s/|,，、]+", product_name) if token]
    if brand:
        product_tokens.append(brand)
    candidates: list[tuple[int, dict[str, Any]]] = []
    for source in sources:
        text = " ".join([source.snippet, source.content])
        for sentence in split_sentences(text):
            if len(sentence) < 8 or len(sentence) > 240:
                continue
            token_hit = any(token and token in sentence for token in product_tokens)
            keyword_hit = any(keyword in sentence for keyword in FACT_KEYWORDS)
            if not (token_hit or keyword_hit):
                continue
            score = host_score(source.url, preferred_domains)
            score += 2 if token_hit else 0
            score += 1 if keyword_hit else 0
            if source.provider in {"tavily", "brave"}:
                score += 1
            candidates.append(
                (
                    score,
                    {
                        "claim": truncate(sentence, 180),
                        "source_url": source.url,
                        "usage": "联网检索候选事实，Agent复核来源和SKU适用性后可用于图文",
                        "confidence": "needs_agent_review",
                        "source_title": source.title,
                    },
                )
            )
    candidates.sort(key=lambda item: item[0], reverse=True)
    facts: list[dict[str, Any]] = []
    seen_claims: set[str] = set()
    for _, fact in candidates:
        claim = fact["claim"]
        if claim in seen_claims:
            continue
        seen_claims.add(claim)
        facts.append(fact)
        if len(facts) >= max_facts:
            break
    return facts


def parse_user_fact(raw: str) -> dict[str, str]:
    if "|" in raw:
        claim, usage = raw.split("|", 1)
    else:
        claim, usage = raw, "用户提供，可用于图文"
    return {"claim": normalize_space(claim), "source_url": "user_provided", "usage": normalize_space(usage)}


def build_research_json(args: argparse.Namespace, provider: str, sources: list[SourceResult]) -> dict[str, Any]:
    preferred_domains = args.preferred_domain or []
    facts = [parse_user_fact(item) for item in args.user_fact]
    facts.extend(
        extract_candidate_facts(
            sources,
            product_name=args.product_name,
            brand=args.brand,
            preferred_domains=preferred_domains,
            max_facts=args.max_facts,
        )
    )
    probable_claims = []
    for source in sources[: args.max_sources_in_output]:
        excerpt = source.snippet or source.content
        if not excerpt:
            continue
        probable_claims.append(
            {
                "claim": truncate(excerpt, 180),
                "reason": f"来自联网来源《{source.title or source.url}》，需Agent复核后使用",
                "source_url": source.url,
            }
        )
    return {
        "product_name": args.product_name,
        "brand": args.brand,
        "target_site": args.target_site,
        "research_date": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "generated_by": "amazon-a-plus-graph/scripts/research_web.py",
        "provider": provider,
        "search_queries": args.query,
        "seed_urls": args.seed_url,
        "source_priority": [
            "用户提供的商品图和包装信息",
            "品牌官网、平台官方店、监管/认证机构页面",
            "权威展会/媒体/行业资料",
            "普通搜索结果仅作线索"
        ],
        "verified_facts": facts,
        "probable_claims": probable_claims,
        "missing_facts": args.missing_fact or DEFAULT_MISSING_FACTS,
        "risk_notes": args.risk_note or DEFAULT_RISK_NOTES,
        "sources": [
            {
                **asdict(source),
                "snippet": truncate(source.snippet, args.excerpt_chars),
                "content": truncate(source.content, args.excerpt_chars),
            }
            for source in sources[: args.max_sources_in_output]
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate research.json from web search/scrape sources.")
    parser.add_argument("--product-name", required=True, help="商品名称")
    parser.add_argument("--brand", default="", help="品牌名")
    parser.add_argument("--target-site", default="", help="目标站点，例如 京东 / Amazon")
    parser.add_argument("--output", required=True, help="research.json 输出路径")
    parser.add_argument("--provider", choices=["auto", "tavily", "brave", "firecrawl", "requests"], default="auto")
    parser.add_argument("--query", action="append", default=[], help="自定义搜索词，可重复")
    parser.add_argument("--seed-url", action="append", default=[], help="直接抓取的URL，可重复")
    parser.add_argument("--preferred-domain", action="append", default=[], help="优先来源域名，可重复，如 mengniu.com.cn")
    parser.add_argument("--domain", action="append", default=[], help="搜索域名过滤，会追加 site:domain，可重复")
    parser.add_argument("--user-fact", action="append", default=[], help="用户已提供事实；格式 claim 或 claim|usage")
    parser.add_argument("--missing-fact", action="append", default=[], help="覆盖默认 missing_facts，可重复")
    parser.add_argument("--risk-note", action="append", default=[], help="覆盖默认 risk_notes，可重复")
    parser.add_argument("--max-results", type=int, default=5, help="每个 query 最大搜索结果数")
    parser.add_argument("--max-facts", type=int, default=12, help="候选事实最大数量")
    parser.add_argument("--max-sources-in-output", type=int, default=12, help="写入 research.json 的来源最大数量")
    parser.add_argument("--excerpt-chars", type=int, default=900, help="sources 中每条摘录最大字符数")
    parser.add_argument("--scrape-results", action=argparse.BooleanOptionalAction, default=True, help="搜索后抓取结果正文")
    parser.add_argument("--scrape-limit", type=int, default=5, help="搜索结果正文抓取上限")
    parser.add_argument("--env-file", default=None, help="指定 .env 路径；默认从脚本目录向上查找")
    parser.add_argument("--timeout", type=int, default=45, help="HTTP 超时秒数")
    parser.add_argument("--sleep", type=float, default=0.2, help="请求间隔秒数")
    parser.add_argument("--search-depth", choices=["basic", "advanced"], default="basic", help="Tavily search_depth")
    parser.add_argument("--tavily-api-url", default=os.getenv("TAVILY_API_URL", "https://api.tavily.com"), help="Tavily API base URL")
    parser.add_argument(
        "--tavily-include-raw-content",
        choices=["none", "text", "markdown", "true"],
        default="text",
        help="Tavily include_raw_content 参数",
    )
    parser.add_argument(
        "--brave-api-url",
        default=os.getenv("BRAVE_SEARCH_API_URL_BASE", "https://api.search.brave.com/res/v1/web/search"),
        help="Brave Web Search endpoint",
    )
    parser.add_argument(
        "--firecrawl-api-url",
        default=os.getenv("FIRECRAWL_API_URL", "https://api.firecrawl.dev/v2"),
        help="Firecrawl API base URL",
    )
    parser.add_argument("--user-agent", default="Mozilla/5.0 (compatible; amazon-a-plus-graph-research/1.0)")
    args = parser.parse_args()
    if args.max_results < 1:
        parser.error("--max-results 必须 >= 1")
    if args.max_facts < 0:
        parser.error("--max-facts 必须 >= 0")
    return args


def main() -> None:
    args = parse_args()
    load_env(args.env_file)
    if not args.query:
        args.query = default_queries(args.product_name, args.brand, args.target_site)
    args.query = apply_domain_filters(args.query, args.domain)
    provider = choose_provider(args)
    sources: list[SourceResult] = []

    if provider == "tavily":
        for query in args.query:
            sources.extend(search_tavily(query, args))
            time.sleep(args.sleep)
    elif provider == "brave":
        for query in args.query:
            sources.extend(search_brave(query, args))
            time.sleep(args.sleep)
    elif provider in {"firecrawl", "requests"} and not args.seed_url:
        raise RuntimeError(f"{provider} provider 需要至少一个 --seed-url")

    sources = dedupe_sources(sources)
    scrape_targets = list(args.seed_url)
    if args.scrape_results:
        scrape_targets.extend(source.url for source in sources if source.url.startswith(("http://", "https://")))
    scrape_targets = list(dict.fromkeys(scrape_targets))[: args.scrape_limit]

    scraped: list[SourceResult] = []
    for url in scrape_targets:
        try:
            if provider == "firecrawl" or (provider in {"tavily", "brave"} and os.getenv("FIRECRAWL_API_KEY")):
                scraped.append(scrape_firecrawl(url, args))
            else:
                scraped.append(scrape_requests(url, args))
        except Exception as exc:
            print(f"[WARN] 抓取失败 {url}: {exc}", file=sys.stderr)
        time.sleep(args.sleep)

    sources = dedupe_sources(scraped + sources)
    if not sources:
        raise RuntimeError("未获得任何联网来源，research.json 未生成")

    research = build_research_json(args, provider, sources)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(research, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                "status": "success",
                "provider": provider,
                "output": str(output),
                "source_count": len(sources),
                "fact_count": len(research["verified_facts"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(json.dumps({"status": "error", "message": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        sys.exit(1)

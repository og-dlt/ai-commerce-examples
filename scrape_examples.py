#!/usr/bin/env python3
"""Collect public examples of consumer-facing shopping/negotiation agents.

This script:
1) checks robots.txt before fetching each page,
2) applies polite per-host rate limiting,
3) extracts evidence snippets for agentic commerce use cases,
4) saves normalized output to data/examples.json.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from urllib.request import Request, urlopen

USER_AGENT = (
    "AgentCommerceResearchBot/1.0 "
    "(public research; respectful crawling; contact: local-run)"
)
DEFAULT_DELAY_SECONDS = 4.0
REQUEST_TIMEOUT_SECONDS = 20


@dataclass(frozen=True)
class Source:
    url: str
    organization: str
    org_home: str
    region_hint: str
    category_hint: str
    terms_url: Optional[str] = None


SOURCES: List[Source] = [
    # US-focused telco/cable bill-negotiation examples.
    Source(
        url="https://www.billshark.com/",
        organization="Billshark",
        org_home="https://www.billshark.com/",
        region_hint="US",
        category_hint="telco",
        terms_url="https://www.billshark.com/terms-of-service",
    ),
    Source(
        url="https://donotpay.com/learn/lower-cable-bill/",
        organization="DoNotPay",
        org_home="https://donotpay.com/",
        region_hint="US",
        category_hint="telco",
        terms_url="https://donotpay.com/terms",
    ),
    Source(
        url="https://www.asktrim.com/how-it-works/",
        organization="Trim",
        org_home="https://www.asktrim.com/",
        region_hint="US",
        category_hint="telco",
        terms_url="https://www.asktrim.com/terms",
    ),
    # US/EU retailer-shopping assistant examples.
    Source(
        url="https://www.klarna.com/us/blog/our-ai-assistant-is-here/",
        organization="Klarna",
        org_home="https://www.klarna.com/",
        region_hint="US/EU",
        category_hint="retail",
        terms_url="https://www.klarna.com/us/terms-and-conditions/",
    ),
    Source(
        url="https://www.amazon.com/b?node=121465724011",
        organization="Amazon",
        org_home="https://www.amazon.com/",
        region_hint="US/EU",
        category_hint="retail",
        terms_url="https://www.amazon.com/gp/help/customer/display.html?nodeId=508088",
    ),
    Source(
        url="https://www.instacart.com/company/updates/introducing-ask-instacart/",
        organization="Instacart",
        org_home="https://www.instacart.com/",
        region_hint="US",
        category_hint="retail",
        terms_url="https://www.instacart.com/help/section/360007996832",
    ),
]

KEYWORDS = [
    "agent",
    "assistant",
    "ai",
    "compare",
    "comparison",
    "shop",
    "buy",
    "purchase",
    "negotiate",
    "call",
    "contact",
    "provider",
    "carrier",
    "retailer",
    "telco",
    "cable",
    "mobile plan",
    "internet plan",
    "best price",
    "best deal",
]


def clean_text(text: str) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", text)
    return [p.strip() for p in parts if len(p.strip()) > 30]


def classify_region(text: str, fallback: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ["united states", "u.s.", "us market", "america"]):
        return "US"
    if any(k in lowered for k in ["europe", "eu", "uk", "germany", "france", "sweden"]):
        return "Europe"
    return fallback


def classify_category(text: str, fallback: str) -> str:
    lowered = text.lower()
    if any(k in lowered for k in ["carrier", "telco", "cable", "internet provider", "mobile plan"]):
        return "telco"
    if any(k in lowered for k in ["retail", "merchant", "shopping", "grocery", "marketplace"]):
        return "retail"
    return fallback


class RespectfulFetcher:
    def __init__(self):
        self.robots_cache: Dict[str, RobotFileParser] = {}
        self.host_last_fetch: Dict[str, float] = {}

    def _robots(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        host = f"{parsed.scheme}://{parsed.netloc}"
        if host in self.robots_cache:
            return self.robots_cache[host]

        robots_url = f"{host}/robots.txt"
        parser = RobotFileParser()
        parser.set_url(robots_url)
        try:
            parser.read()
        except Exception:
            # On robots retrieval failure, default to disallow for safety.
            parser = RobotFileParser()
            parser.parse(["User-agent: *", "Disallow: /"])
        self.robots_cache[host] = parser
        return parser

    def allowed(self, url: str) -> bool:
        parser = self._robots(url)
        return bool(parser.can_fetch(USER_AGENT, url))

    def crawl_delay(self, url: str) -> float:
        parser = self._robots(url)
        try:
            delay = parser.crawl_delay(USER_AGENT)
            if delay is None:
                delay = parser.crawl_delay("*")
            if isinstance(delay, (int, float)) and delay > 0:
                return float(delay)
        except Exception:
            pass
        return DEFAULT_DELAY_SECONDS

    def get(self, url: str) -> Optional[str]:
        if not self.allowed(url):
            print(f"Skipping (robots disallow): {url}")
            return None

        parsed = urlparse(url)
        host = parsed.netloc
        now = time.time()
        delay = self.crawl_delay(url)
        if host in self.host_last_fetch:
            elapsed = now - self.host_last_fetch[host]
            if elapsed < delay:
                time.sleep(delay - elapsed)

        request = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        try:
            with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                status = getattr(response, "status", 200)
                if status >= 400:
                    print(f"Skipping ({status}): {url}")
                    return None
                body = response.read().decode("utf-8", errors="replace")
                self.host_last_fetch[host] = time.time()
                return body
        except Exception as exc:
            print(f"Skipping (request failed): {url} :: {exc}")
            return None


def extract_example(source: Source, html: str) -> Optional[dict]:
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html, flags=re.IGNORECASE | re.DOTALL)
    raw_title = title_match.group(1) if title_match else source.organization
    title = clean_text(re.sub(r"<[^>]+>", " ", raw_title))
    text = clean_text(re.sub(r"<[^>]+>", " ", html))
    lowered = text.lower()

    if not any(keyword in lowered for keyword in KEYWORDS):
        return None

    candidate_sentences = [
        sentence
        for sentence in split_sentences(text)
        if any(keyword in sentence.lower() for keyword in KEYWORDS)
    ]
    if not candidate_sentences:
        return None

    evidence = candidate_sentences[0][:500]
    summary = " ".join(candidate_sentences[:2])[:700]
    region = classify_region(text, source.region_hint)
    category = classify_category(text, source.category_hint)
    timestamp = datetime.now(timezone.utc).isoformat()

    return {
        "organization": source.organization,
        "organization_home": source.org_home,
        "source_url": source.url,
        "source_title": title,
        "terms_url": source.terms_url,
        "region": region,
        "category": category,
        "summary": summary,
        "evidence_snippet": evidence,
        "compliance": {
            "public_page": True,
            "robots_checked": True,
            "terms_review_note": "Source page is public; manual legal review still recommended.",
        },
        "scraped_at_utc": timestamp,
    }


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")


def main() -> None:
    fetcher = RespectfulFetcher()

    examples: List[dict] = []
    for source in SOURCES:
        html = fetcher.get(source.url)
        if not html:
            continue
        example = extract_example(source, html)
        if example:
            examples.append(example)
            print(f"Collected: {source.organization}")
        else:
            print(f"No match: {source.organization}")

    # Deduplicate by source_url while preserving order.
    deduped = []
    seen = set()
    for item in examples:
        key = item["source_url"]
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)

    output = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "count": len(deduped),
        "query": "Public examples of agents that buy/compare/negotiate on behalf of consumers in US/Europe.",
        "examples": deduped,
    }

    save_json(Path("data/examples.json"), output)
    print(f"Saved {len(deduped)} examples to data/examples.json")


if __name__ == "__main__":
    main()

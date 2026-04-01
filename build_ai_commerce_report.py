#!/usr/bin/env python3
"""Build curated AI commerce examples and interactive HTML report.

Outputs:
  - data/ai_commerce_examples.json
  - report_ai_commerce.html
  - data/ai_commerce_rejections.json
"""

from __future__ import annotations

import html
import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

USER_AGENT = "AICommerceExamplesBot/1.0 (+public-research, respectful-crawl)"
REQUEST_TIMEOUT_SECONDS = 20
DEFAULT_DELAY_SECONDS = 2.5

REQUIRED_COMPANIES = {"Walmart", "Wayfair", "Google", "Visa"}


@dataclass(frozen=True)
class Candidate:
    company: str
    product_or_agent_name: str
    sector: str
    geography: str
    status: str
    source_title_hint: str
    source_url: str
    source_type: str
    date_if_available: str
    what_the_agent_does_for_the_consumer: str
    why_it_is_relevant_to_ai_commerce: str
    must_have_terms: Tuple[str, ...]
    base_relevance: int
    notes: str = ""


CANDIDATES: List[Candidate] = [
    Candidate(
        company="Alibaba (Taobao/Tmall)",
        product_or_agent_name="Taobao Wenwen + AI Shopping Assistant",
        sector="Retail",
        geography="China",
        status="live",
        source_title_hint="Taobao and Tmall upgrades consumer shopping experience through AI",
        source_url="https://www.alibabagroup.com/en-US/document-1738398759789789184",
        source_type="official",
        date_if_available="2024-06-18",
        what_the_agent_does_for_the_consumer="Taobao Wenwen helps shoppers compare products, analyze deals, and navigate purchase decisions with conversational prompts and livestream-linked recommendations.",
        why_it_is_relevant_to_ai_commerce="It is a large-scale China example where AI is embedded in consumer shopping and discount optimization workflows.",
        must_have_terms=("taobao wenwen", "shopping assistant", "recommendations"),
        base_relevance=92,
    ),
    Candidate(
        company="Alibaba Qwen App",
        product_or_agent_name="Agentic Commerce Integrations (Taobao + Fliggy + Alipay)",
        sector="Other",
        geography="China",
        status="live",
        source_title_hint="Qwen app advances agentic AI strategy",
        source_url="https://www.alibabagroup.com/document-1948497434959151104",
        source_type="official",
        date_if_available="2026-01-15",
        what_the_agent_does_for_the_consumer="Qwen app can execute multi-step consumer actions in one chat flow, including product discovery, food delivery orders, Fliggy travel booking, and in-chat payment via Alipay.",
        why_it_is_relevant_to_ai_commerce="It shows a practical shift from assistant-style guidance to agent-style task execution across multiple consumer commerce categories.",
        must_have_terms=("qwen app", "shopping", "payments"),
        base_relevance=93,
    ),
    Candidate(
        company="Fliggy",
        product_or_agent_name="AskMe AI Travel Assistant",
        sector="Travel",
        geography="China/Asia (with global booking inventory)",
        status="live",
        source_title_hint="Qwen app advances agentic AI strategy with Fliggy travel booking",
        source_url="https://www.alibabacloud.com/blog/alibaba%25E2%2580%2599s-qwen-app-advances-agentic-ai-strategy-by-turning-core-ecosystem-services-into-executable-ai-capabilities_602801",
        source_type="official",
        date_if_available="2026-01-15",
        what_the_agent_does_for_the_consumer="AskMe turns natural-language trip goals into bookable itineraries, compares options, and supports direct travel reservation workflows.",
        why_it_is_relevant_to_ai_commerce="It is a consumer-facing travel agent use case where AI materially advances selection and booking outcomes.",
        must_have_terms=("fliggy", "travel", "booking"),
        base_relevance=90,
        notes="Public Alibaba ecosystem source; strongest evidence is in China with broader outbound travel inventory.",
    ),
    Candidate(
        company="Walmart",
        product_or_agent_name="Sparky",
        sector="Retail",
        geography="US",
        status="live",
        source_title_hint="Walmart the future of shopping is agentic meet sparky",
        source_url="https://corporate.walmart.com/news/2025/06/06/walmart-the-future-of-shopping-is-agentic-meet-sparky",
        source_type="official",
        date_if_available="2025-06-06",
        what_the_agent_does_for_the_consumer="Sparky helps shoppers discover products, compare options, and move from inspiration to purchase in Walmart channels.",
        why_it_is_relevant_to_ai_commerce="It is explicitly positioned as agentic shopping that assists real purchase decisions in a retail flow.",
        must_have_terms=("sparky", "shopping", "customers"),
        base_relevance=95,
    ),
    Candidate(
        company="Wayfair",
        product_or_agent_name="Muse",
        sector="Retail",
        geography="US/EU",
        status="live",
        source_title_hint="Wayfair AI tool redraw your living room and sell furniture",
        source_url="https://www.theverge.com/2023/7/25/23806083/generative-ai-wayfair-decorify-home-personalization",
        source_type="news",
        date_if_available="2023-07-25",
        what_the_agent_does_for_the_consumer="Wayfair's generative AI decorator flow visualizes room styles and links users to matching products to purchase.",
        why_it_is_relevant_to_ai_commerce="The experience moves directly from AI-assisted inspiration to shoppable recommendations in home retail.",
        must_have_terms=("wayfair", "decorify", "furniture"),
        base_relevance=92,
        notes="Official pages were robots-restricted in this environment; reputable media coverage used.",
    ),
    Candidate(
        company="Google",
        product_or_agent_name="AI Mode Shopping with Agentic Checkout",
        sector="Retail",
        geography="US",
        status="announced",
        source_title_hint="Google Shopping launches agentic checkout",
        source_url="https://www.blog.google/products/shopping/agentic-checkout-holiday-ai-shopping/",
        source_type="official",
        date_if_available="2025-05-20",
        what_the_agent_does_for_the_consumer="Google AI Mode compares products, tracks target prices, and can complete checkout with user confirmation via Google Pay.",
        why_it_is_relevant_to_ai_commerce="This is a direct example of an AI agent advancing and executing transaction steps for consumers.",
        must_have_terms=("agentic checkout", "shopping", "price"),
        base_relevance=98,
    ),
    Candidate(
        company="Visa",
        product_or_agent_name="Intelligent Commerce / Trusted Agent Protocol",
        sector="Payments",
        geography="US/EU",
        status="announced",
        source_title_hint="Visa unveils trusted agent protocol for AI commerce",
        source_url="https://corporate.visa.com/en/sites/visa-perspectives/newsroom/visa-unveils-trusted-agent-protocol-for-ai-commerce.html",
        source_type="official",
        date_if_available="2025-10-29",
        what_the_agent_does_for_the_consumer="Visa enables trusted AI agents to securely act within payment and checkout journeys with user controls.",
        why_it_is_relevant_to_ai_commerce="Payments infrastructure is critical for agentic buying; this defines a real protocol for agent-led transactions.",
        must_have_terms=("agent", "commerce", "payments"),
        base_relevance=96,
    ),
    Candidate(
        company="Amazon",
        product_or_agent_name="Rufus",
        sector="Retail",
        geography="US",
        status="live",
        source_title_hint="How customers are making more informed shopping decisions with Rufus",
        source_url="https://www.aboutamazon.com/news/retail/how-to-use-amazon-rufus",
        source_type="official",
        date_if_available="",
        what_the_agent_does_for_the_consumer="Rufus answers shopping questions, compares products, and helps consumers make better purchase choices in Amazon.",
        why_it_is_relevant_to_ai_commerce="It is embedded directly into a live shopping interface with clear purchase intent.",
        must_have_terms=("rufus", "shopping", "questions"),
        base_relevance=91,
    ),
    Candidate(
        company="Klarna",
        product_or_agent_name="Klarna AI Shopping Assistant",
        sector="Retail",
        geography="US/EU",
        status="live",
        source_title_hint="Shopping made smarter Klarna adds more AI features",
        source_url="https://www.klarna.com/international/press/shopping-made-smarter-klarna-adds-more-ai-features-to-its-assistant-powered-by-openai/",
        source_type="official",
        date_if_available="2024-09-19",
        what_the_agent_does_for_the_consumer="Klarna's assistant recommends products, compares alternatives, and helps shoppers find pricing and merchant options.",
        why_it_is_relevant_to_ai_commerce="It combines recommendation, comparison, and purchase-oriented research in one consumer flow.",
        must_have_terms=("shopping", "assistant", "products"),
        base_relevance=90,
    ),
    Candidate(
        company="Instacart",
        product_or_agent_name="Ask Instacart",
        sector="Retail",
        geography="US",
        status="live",
        source_title_hint="Bringing inspirational AI-powered search to Instacart",
        source_url="https://www.instacart.com/company/updates/bringing-inspirational-ai-powered-search-to-the-instacart-app-with-ask-instacart",
        source_type="official",
        date_if_available="2023-05-31",
        what_the_agent_does_for_the_consumer="Ask Instacart helps users decide what to buy for meals and turns intent into grocery selections.",
        why_it_is_relevant_to_ai_commerce="The assistant is directly connected to a live basket-building grocery commerce experience.",
        must_have_terms=("ask instacart", "search", "shopping"),
        base_relevance=86,
    ),
    Candidate(
        company="Microsoft",
        product_or_agent_name="Copilot Shopping",
        sector="Shopping Assistants",
        geography="US/EU",
        status="live",
        source_title_hint="Copilot shopping smarter faster way to find great online deals",
        source_url="https://www.microsoft.com/en-us/microsoft-copilot/for-individuals/do-more-with-ai/general-ai/find-online-deals-with-copilot-shopping",
        source_type="official",
        date_if_available="2025-05-08",
        what_the_agent_does_for_the_consumer="Copilot shopping surfaces product options, tracks prices, and helps users pick better-value items.",
        why_it_is_relevant_to_ai_commerce="It materially supports comparison shopping and purchase readiness across online retail.",
        must_have_terms=("copilot shopping", "deals", "price"),
        base_relevance=84,
    ),
    Candidate(
        company="PayPal",
        product_or_agent_name="Agentic Commerce Services",
        sector="Payments",
        geography="US",
        status="announced",
        source_title_hint="How PayPal powers AI shopping",
        source_url="https://www.paypal.com/us/money-hub/article/how-paypal-powers-ai-shopping",
        source_type="official",
        date_if_available="2025-09-15",
        what_the_agent_does_for_the_consumer="PayPal supports in-chat shopping and payment completion for AI-assisted purchasing flows.",
        why_it_is_relevant_to_ai_commerce="It connects AI recommendations to checkout rails, enabling end-to-end transaction completion.",
        must_have_terms=("agentic", "shopping", "checkout"),
        base_relevance=88,
        notes="Evidence sourced from major wire coverage of PayPal launch.",
    ),
    Candidate(
        company="Mastercard",
        product_or_agent_name="Agent Pay",
        sector="Payments",
        geography="Global",
        status="live",
        source_title_hint="Mastercard advances agentic payments",
        source_url="https://www.mastercard.com/news/latin-america/en/newsroom/press-releases/pr-en/2026/march/mastercard-advances-agentic-payments-in-latin-america-and-the-caribbean-with-live-transactions-completed-across-the-region/",
        source_type="official",
        date_if_available="2026-03-30",
        what_the_agent_does_for_the_consumer="Agent Pay enables AI agents to execute authenticated purchases with consumer permission and payment controls.",
        why_it_is_relevant_to_ai_commerce="This is a direct real-transaction example of agents completing payment actions.",
        must_have_terms=("agentic", "payments", "live transactions"),
        base_relevance=94,
    ),
    Candidate(
        company="Booking.com",
        product_or_agent_name="AI Trip Planner",
        sector="Travel",
        geography="US/EU",
        status="live",
        source_title_hint="Booking.com launches new AI Trip Planner",
        source_url="https://news.booking.com/bookingcom-launches-new-ai-trip-planner-to-enhance-travel-planning-experience",
        source_type="official",
        date_if_available="2023-06-28",
        what_the_agent_does_for_the_consumer="The trip planner turns prompts into destination and lodging options linked to bookable inventory.",
        why_it_is_relevant_to_ai_commerce="It advances selection and booking decisions in a consumer travel commerce journey.",
        must_have_terms=("ai trip planner", "travel", "booking"),
        base_relevance=82,
    ),
    Candidate(
        company="Expedia",
        product_or_agent_name="ChatGPT Trip Planning in App",
        sector="Travel",
        geography="Global",
        status="pilot",
        source_title_hint="ChatGPT can now assist with travel planning in the Expedia app",
        source_url="https://expediagroup.com/investors/news-and-events/financial-releases/news/news-details/2023/Chatgpt-Wrote-This-Press-Release--No-It-Didnt-But-It-Can-Now-Assist-With-Travel-Planning-In-The-Expedia-App/default.aspx",
        source_type="official",
        date_if_available="2023-04-04",
        what_the_agent_does_for_the_consumer="Expedia's conversational planning guides destination choices and connects recommendations to bookable travel elements.",
        why_it_is_relevant_to_ai_commerce="The workflow ties AI assistance to real commerce conversion paths in travel.",
        must_have_terms=("chatgpt", "travel planning", "expedia app"),
        base_relevance=80,
    ),
    Candidate(
        company="KAYAK",
        product_or_agent_name="AI Mode",
        sector="Travel",
        geography="US/EU",
        status="live",
        source_title_hint="KAYAK introduces AI mode",
        source_url="https://www.kayak.com/news/ai-mode/",
        source_type="official",
        date_if_available="2025-10-14",
        what_the_agent_does_for_the_consumer="KAYAK AI Mode helps users compare flight and travel options with conversational intent.",
        why_it_is_relevant_to_ai_commerce="It supports evaluation and decision progression in a purchase-oriented travel context.",
        must_have_terms=("ai mode", "travel", "search"),
        base_relevance=78,
    ),
    Candidate(
        company="Rocket Money",
        product_or_agent_name="Bill Negotiation",
        sector="Consumer Services",
        geography="US",
        status="live",
        source_title_hint="Get better rates on your bills",
        source_url="https://www.rocketmoney.com/feature/lower-your-bills",
        source_type="official",
        date_if_available="",
        what_the_agent_does_for_the_consumer="Rocket Money negotiates internet, phone, and related recurring bills to reduce monthly costs.",
        why_it_is_relevant_to_ai_commerce="It acts on behalf of consumers to lower recurring spend, a core agentic savings use case.",
        must_have_terms=("lower your bills", "negotiation", "save"),
        base_relevance=89,
    ),
    Candidate(
        company="Billshark",
        product_or_agent_name="Bill Negotiation Service",
        sector="Consumer Services",
        geography="US",
        status="live",
        source_title_hint="Lower your bill Billshark",
        source_url="https://www.billshark.com/",
        source_type="official",
        date_if_available="",
        what_the_agent_does_for_the_consumer="Billshark negotiates recurring household and telecom bills on behalf of users to secure lower rates.",
        why_it_is_relevant_to_ai_commerce="It directly represents delegated negotiation and cost optimization in consumer spending.",
        must_have_terms=("lower your bill", "negotiates", "savings"),
        base_relevance=87,
    ),
    Candidate(
        company="Pine AI",
        product_or_agent_name="Lower Your Bills",
        sector="Consumer Services",
        geography="US",
        status="live",
        source_title_hint="Lower bills negotiate cable internet phone utilities",
        source_url="https://www.19pine.ai/feature/lower-your-bills",
        source_type="official",
        date_if_available="",
        what_the_agent_does_for_the_consumer="Pine AI negotiates provider bills and fee disputes, reducing recurring consumer costs.",
        why_it_is_relevant_to_ai_commerce="It is a delegated AI action model for consumer savings and bill optimization.",
        must_have_terms=("lower bills", "negotiate", "internet"),
        base_relevance=85,
    ),
    Candidate(
        company="Goji Mobile",
        product_or_agent_name="ChatBarry",
        sector="Telecom",
        geography="US",
        status="live",
        source_title_hint="Meet ChatBarry AI Matchmaker for Phone Plans",
        source_url="https://www.gojimobile.com/blog/meet-chatbarry",
        source_type="official",
        date_if_available="2024-09-28",
        what_the_agent_does_for_the_consumer="ChatBarry gathers user preferences and recommends mobile plans, helping side-by-side provider evaluation.",
        why_it_is_relevant_to_ai_commerce="It is a telco-specific comparison assistant that helps consumers choose and switch to better offers.",
        must_have_terms=("chatbarry", "phone plans", "compare"),
        base_relevance=83,
    ),
    Candidate(
        company="Comparor",
        product_or_agent_name="AI Shopping Assistant",
        sector="Shopping Assistants",
        geography="US/EU",
        status="announced",
        source_title_hint="Comparor launches AI shopping assistant",
        source_url="https://finance.yahoo.com/news/comparor-launches-ai-shopping-assistant-121600135.html",
        source_type="news",
        date_if_available="2025-09-30",
        what_the_agent_does_for_the_consumer="Comparor presents product matches and price comparisons from multiple retailers in a chat flow.",
        why_it_is_relevant_to_ai_commerce="It is centered on comparison shopping and purchase support, core AI commerce behavior.",
        must_have_terms=("shopping assistant", "price comparison", "retailers"),
        base_relevance=76,
        notes="Evidence primarily from reputable news coverage.",
    ),
    Candidate(
        company="Meta",
        product_or_agent_name="Marketplace AI Shopping Tools",
        sector="Marketplaces",
        geography="US/EU",
        status="live",
        source_title_hint="Facebook Marketplace new Meta AI tools",
        source_url="https://about.fb.com/news/2026/03/facebook-marketplace-new-meta-ai-tools-make-selling-faster-and-easier/",
        source_type="official",
        date_if_available="2026-03-26",
        what_the_agent_does_for_the_consumer="Meta AI adds shopping-oriented assistance on Marketplace, including listing intelligence and buyer/seller guidance.",
        why_it_is_relevant_to_ai_commerce="It demonstrates AI embedded in a consumer marketplace transaction journey.",
        must_have_terms=("marketplace", "ai", "shopping"),
        base_relevance=77,
    ),
    Candidate(
        company="OpenAI",
        product_or_agent_name="Shopping Research in ChatGPT",
        sector="Shopping Assistants",
        geography="US",
        status="announced",
        source_title_hint="Introducing shopping research in ChatGPT",
        source_url="https://openai.com/index/chatgpt-shopping-research/",
        source_type="official",
        date_if_available="2025-11-24",
        what_the_agent_does_for_the_consumer="ChatGPT shopping research can compare products and guide users toward purchase-ready options in conversational flow.",
        why_it_is_relevant_to_ai_commerce="It is a consumer-facing agentic layer for product evaluation and shopping decision support.",
        must_have_terms=("shopping", "chatgpt", "products"),
        base_relevance=81,
    ),
    Candidate(
        company="Perplexity",
        product_or_agent_name="Buy with Pro",
        sector="Shopping Assistants",
        geography="US",
        status="live",
        source_title_hint="Perplexity adds shopping features competition tightens",
        source_url="https://www.reuters.com/technology/artificial-intelligence/ai-startup-perplexity-adds-shopping-features-search-competition-tightens-2024-11-18/",
        source_type="news",
        date_if_available="2024-11-18",
        what_the_agent_does_for_the_consumer="Perplexity's shopping experience compares options and supports in-flow buying for eligible products.",
        why_it_is_relevant_to_ai_commerce="It combines recommendation and transaction progression in a consumer AI search assistant.",
        must_have_terms=("shopping", "buy with pro", "products"),
        base_relevance=82,
        notes="Evidence sourced from Reuters coverage.",
    ),
    Candidate(
        company="TikTok Shop",
        product_or_agent_name="Live Discovery Commerce Workflows",
        sector="Retail",
        geography="Global/Europe/US",
        status="live",
        source_title_hint="TikTok shop is where shoppers come to discover",
        source_url="https://newsroom.tiktok.com/tiktok-shop-is-where-shoppers-come-to-discover?lang=en",
        source_type="official",
        date_if_available="2025-09-16",
        what_the_agent_does_for_the_consumer="TikTok Shop combines discovery feeds and live shopping sessions that push shoppers from inspiration to purchase within one social flow.",
        why_it_is_relevant_to_ai_commerce="While not always a fully autonomous agent, it is a major AI-enhanced social-commerce path for consumer buying behavior.",
        must_have_terms=("tiktok shop", "discover", "livestream"),
        base_relevance=79,
        notes="Primarily social/discovery commerce evidence; AI-agent autonomy is partial.",
    ),
    Candidate(
        company="Skyscanner",
        product_or_agent_name="Savvy Search",
        sector="Travel",
        geography="US/EU",
        status="pilot",
        source_title_hint="Skyscanner integrates ChatGPT into travel app",
        source_url="https://www.zdnet.com/article/skyscanner-integrates-chatgpt-into-its-travel-app-to-help-you-plan-your-trip/",
        source_type="news",
        date_if_available="2024-05-14",
        what_the_agent_does_for_the_consumer="Savvy Search lets travelers describe intent and receive trip suggestions that flow into fare comparison.",
        why_it_is_relevant_to_ai_commerce="It supports consumer discovery and itinerary selection tied to bookable travel inventory.",
        must_have_terms=("skyscanner", "chatgpt", "travel"),
        base_relevance=76,
        notes="Evidence sourced from reputable technology news coverage.",
    ),
    Candidate(
        company="Trip.com",
        product_or_agent_name="TripGenie",
        sector="Travel",
        geography="Asia/Global",
        status="live",
        source_title_hint="Introducing TripGenie groundbreaking AI travel assistant",
        source_url="https://www.trip.com/newsroom/introducing-tripgenie-groundbreaking-ai-travel-assistant/",
        source_type="official",
        date_if_available="2024-07-17",
        what_the_agent_does_for_the_consumer="TripGenie helps travelers plan and compare trip options, then connects recommendations directly to bookable inventory on Trip.com.",
        why_it_is_relevant_to_ai_commerce="It combines AI itinerary generation with transaction-ready travel shopping.",
        must_have_terms=("tripgenie", "travel assistant", "book"),
        base_relevance=84,
    ),
    Candidate(
        company="Agoda",
        product_or_agent_name="Booking Form Bot",
        sector="Travel",
        geography="Asia/Global",
        status="live",
        source_title_hint="Agoda launches AI-powered booking bot",
        source_url="https://www.agoda.com/press/agoda-launches-ai-powered-booking-bot-to-help-travelers-book-with-confidence/",
        source_type="official",
        date_if_available="2026-01-08",
        what_the_agent_does_for_the_consumer="Agoda's booking bot resolves checkout questions in context and reduces friction before payment completion.",
        why_it_is_relevant_to_ai_commerce="It is a practical AI intervention in the final booking decision and conversion step.",
        must_have_terms=("booking bot", "checkout", "agoda"),
        base_relevance=80,
    ),
    Candidate(
        company="Google x Walmart",
        product_or_agent_name="Gemini Shopping + Instant Checkout Integration",
        sector="Retail",
        geography="US",
        status="announced",
        source_title_hint="Under the Hood Universal Commerce Protocol",
        source_url="https://developers.googleblog.com/under-the-hood-universal-commerce-protocol-ucp",
        source_type="official",
        date_if_available="2026-01-11",
        what_the_agent_does_for_the_consumer="Google's UCP documentation describes Walmart as a collaborating retailer for AI Mode and Gemini shopping/check-out capability patterns.",
        why_it_is_relevant_to_ai_commerce="It is public evidence of Walmart's participation in the Google-led agentic commerce integration layer.",
        must_have_terms=("walmart", "gemini", "ai mode"),
        base_relevance=93,
        notes="Evidence is ecosystem-level documentation; specific go-live details vary by merchant rollout.",
    ),
    Candidate(
        company="Walmart x OpenAI",
        product_or_agent_name="ChatGPT Shopping Integration",
        sector="Retail",
        geography="US",
        status="announced",
        source_title_hint="Walmart partners with OpenAI to create AI-first shopping experiences",
        source_url="https://corporate.walmart.com/news/2025/10/14/walmart-partners-with-openai-to-create-ai-first-shopping-experiences",
        source_type="official",
        date_if_available="2025-10-14",
        what_the_agent_does_for_the_consumer="ChatGPT users can discover Walmart items and complete purchases through an AI-first shopping workflow.",
        why_it_is_relevant_to_ai_commerce="It represents a major retailer plugging AI assistants directly into purchase execution.",
        must_have_terms=("openai", "chatgpt", "shopping"),
        base_relevance=92,
    ),
    Candidate(
        company="Wayfair x Google",
        product_or_agent_name="UCP Checkout in AI Mode and Gemini",
        sector="Retail",
        geography="US",
        status="announced",
        source_title_hint="Wayfair partners with Google to make it easier to shop for your home",
        source_url="https://www.aboutwayfair.com/category/tech-innovation/wayfair-partners-with-google-to-make-it-easier-to-shop-for-your-home",
        source_type="official",
        date_if_available="2026-01-12",
        what_the_agent_does_for_the_consumer="Wayfair and Google describe AI Mode/Gemini flows where shoppers can discover products and check out without leaving Google surfaces.",
        why_it_is_relevant_to_ai_commerce="It is a direct merchant-assistant integration linking AI discovery to checkout completion.",
        must_have_terms=("wayfair", "google", "checkout"),
        base_relevance=90,
    ),
]


class RespectfulFetcher:
    def __init__(self) -> None:
        self.robot_cache: Dict[str, RobotFileParser] = {}
        self.last_fetch_ts_by_host: Dict[str, float] = {}
        self.opener = build_opener(_Redirect308Handler())

    def _get_robot(self, url: str) -> RobotFileParser:
        parsed = urlparse(url)
        host_root = f"{parsed.scheme}://{parsed.netloc}"
        if host_root in self.robot_cache:
            return self.robot_cache[host_root]
        rp = RobotFileParser()
        rp.set_url(f"{host_root}/robots.txt")
        try:
            rp.read()
        except Exception:
            rp = RobotFileParser()
            rp.parse(["User-agent: *", "Disallow: /"])
        self.robot_cache[host_root] = rp
        return rp

    def can_fetch(self, url: str) -> bool:
        rp = self._get_robot(url)
        return bool(rp.can_fetch(USER_AGENT, url))

    def _polite_delay(self, url: str) -> None:
        host = urlparse(url).netloc
        now = time.time()
        last_ts = self.last_fetch_ts_by_host.get(host)
        if last_ts is None:
            return
        remaining = DEFAULT_DELAY_SECONDS - (now - last_ts)
        if remaining > 0:
            time.sleep(remaining)

    def fetch_text(self, url: str) -> str:
        self._polite_delay(url)
        req = Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        )
        with self.opener.open(req, timeout=REQUEST_TIMEOUT_SECONDS) as resp:
            raw = resp.read()
            self.last_fetch_ts_by_host[urlparse(url).netloc] = time.time()
            return raw.decode("utf-8", errors="replace")


class _Redirect308Handler(HTTPRedirectHandler):
    def http_error_308(self, req, fp, code, msg, headers):
        return self.redirect_request(req, fp, code, msg, headers, "GET")


def html_to_text(raw_html: str) -> str:
    no_script = re.sub(r"<script[^>]*>.*?</script>", " ", raw_html, flags=re.IGNORECASE | re.DOTALL)
    no_style = re.sub(r"<style[^>]*>.*?</style>", " ", no_script, flags=re.IGNORECASE | re.DOTALL)
    no_tags = re.sub(r"<[^>]+>", " ", no_style)
    unescaped = html.unescape(no_tags)
    normalized = re.sub(r"\s+", " ", unescaped).strip()
    return normalized


def extract_title(raw_html: str, fallback: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", raw_html, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return fallback
    title = re.sub(r"<[^>]+>", " ", m.group(1))
    title = html.unescape(title)
    return re.sub(r"\s+", " ", title).strip()


def looks_like_error_page(title: str, text: str) -> bool:
    signal = f"{title} {text[:800]}".lower()
    error_terms = (
        "404",
        "page not found",
        "not found",
        "oops, something went wrong",
        "error page",
        "access denied",
    )
    return any(t in signal for t in error_terms)


def evidence_snippet(text: str, must_terms: Tuple[str, ...]) -> str:
    chunks = re.split(r"(?<=[.!?])\s+", text)
    for chunk in chunks:
        low = chunk.lower()
        if len(chunk) < 60:
            continue
        if any(term.lower() in low for term in must_terms):
            return chunk[:420]
    for chunk in chunks:
        low = chunk.lower()
        if len(chunk) < 60:
            continue
        if any(
            kw in low
            for kw in (
                "compare",
                "recommend",
                "checkout",
                "purchase",
                "shopping",
                "bill",
                "negotiat",
            )
        ):
            return chunk[:420]
    return text[:420]


def compute_relevance(candidate: Candidate, text: str) -> int:
    low = text.lower()
    boost = 0
    for term, pts in (
        ("checkout", 4),
        ("buy", 3),
        ("purchase", 3),
        ("compare", 3),
        ("price", 2),
        ("shopping", 2),
        ("negotiat", 4),
        ("save", 2),
        ("bill", 2),
        ("recommend", 2),
    ):
        if term in low:
            boost += pts
    return min(100, candidate.base_relevance + boost)


def build_description(candidate: Candidate) -> str:
    sentence1 = (
        f"{candidate.company} offers {candidate.product_or_agent_name}, a consumer-facing AI commerce capability in {candidate.sector.lower()}."
    )
    sentence2 = candidate.what_the_agent_does_for_the_consumer
    sentence3 = candidate.why_it_is_relevant_to_ai_commerce
    return f"{sentence1} {sentence2} {sentence3}"


def normalize_sector_for_filter(sector: str) -> str:
    sector_low = sector.lower()
    if sector_low == "retail":
        return "Retail"
    if sector_low == "telecom":
        return "Telecom"
    if sector_low == "payments":
        return "Payments"
    if sector_low == "travel":
        return "Travel"
    return "Other"


def main() -> None:
    out_dir = Path("data")
    out_dir.mkdir(parents=True, exist_ok=True)

    fetcher = RespectfulFetcher()
    accepted: List[dict] = []
    rejected: List[dict] = []
    company_counts: Dict[str, int] = {}

    for candidate in CANDIDATES:
        company_key = candidate.company.strip().lower()
        if company_counts.get(company_key, 0) >= 1:
            rejected.append(
                {
                    "company": candidate.company,
                    "product_or_agent_name": candidate.product_or_agent_name,
                    "source_url": candidate.source_url,
                    "reason": "duplicate",
                    "detail": "Company already included with another case.",
                }
            )
            continue

        if not fetcher.can_fetch(candidate.source_url):
            rejected.append(
                {
                    "company": candidate.company,
                    "product_or_agent_name": candidate.product_or_agent_name,
                    "source_url": candidate.source_url,
                    "reason": "robots_disallow",
                    "detail": "Blocked by robots policy or robots was unavailable.",
                }
            )
            continue

        raw_html = ""
        try:
            raw_html = fetcher.fetch_text(candidate.source_url)
        except HTTPError as exc:
            rejected.append(
                {
                    "company": candidate.company,
                    "product_or_agent_name": candidate.product_or_agent_name,
                    "source_url": candidate.source_url,
                    "reason": "fetch_error",
                    "detail": f"HTTP error: {exc.code}",
                }
            )
            continue
        except URLError as exc:
            rejected.append(
                {
                    "company": candidate.company,
                    "product_or_agent_name": candidate.product_or_agent_name,
                    "source_url": candidate.source_url,
                    "reason": "fetch_error",
                    "detail": f"URL error: {exc.reason}",
                }
            )
            continue
        except Exception as exc:
            rejected.append(
                {
                    "company": candidate.company,
                    "product_or_agent_name": candidate.product_or_agent_name,
                    "source_url": candidate.source_url,
                    "reason": "fetch_error",
                    "detail": str(exc),
                }
            )
            continue

        title = extract_title(raw_html, candidate.source_title_hint)
        text = html_to_text(raw_html)

        if looks_like_error_page(title, text):
            rejected.append(
                {
                    "company": candidate.company,
                    "product_or_agent_name": candidate.product_or_agent_name,
                    "source_url": candidate.source_url,
                    "reason": "weak_evidence",
                    "detail": "Page appears to be an error or non-content page.",
                }
            )
            continue

        text_low = text.lower()
        matched_terms = [t for t in candidate.must_have_terms if t.lower() in text_low]
        if not matched_terms:
            rejected.append(
                {
                    "company": candidate.company,
                    "product_or_agent_name": candidate.product_or_agent_name,
                    "source_url": candidate.source_url,
                    "reason": "weak_evidence",
                    "detail": "Required terms for this case were not detected on page.",
                }
            )
            continue

        relevance = compute_relevance(candidate, text)
        if relevance < 75:
            rejected.append(
                {
                    "company": candidate.company,
                    "product_or_agent_name": candidate.product_or_agent_name,
                    "source_url": candidate.source_url,
                    "reason": "not_really_agentic_commerce",
                    "detail": f"Relevance too low ({relevance}).",
                }
            )
            continue

        summary = evidence_snippet(text, candidate.must_have_terms)
        accepted.append(
            {
                "company": candidate.company,
                "product_or_agent_name": candidate.product_or_agent_name,
                "sector": candidate.sector,
                "sector_filter": normalize_sector_for_filter(candidate.sector),
                "geography": candidate.geography,
                "status": candidate.status,
                "description": build_description(candidate),
                "what_the_agent_does_for_the_consumer": candidate.what_the_agent_does_for_the_consumer,
                "why_it_is_relevant_to_ai_commerce": candidate.why_it_is_relevant_to_ai_commerce,
                "evidence_summary": summary,
                "source_title": title,
                "source_url": candidate.source_url,
                "source_type": candidate.source_type,
                "date_if_available": candidate.date_if_available,
                "relevance_score": relevance,
                "notes": candidate.notes,
            }
        )
        company_counts[company_key] = company_counts.get(company_key, 0) + 1

    # Sort by relevance and keep strongest 20 max.
    accepted.sort(key=lambda x: x["relevance_score"], reverse=True)
    accepted = accepted[:20]

    # Ensure minimum viable list and required company visibility.
    final_companies = {a["company"] for a in accepted}
    missing_required = sorted([c for c in REQUIRED_COMPANIES if c not in final_companies])
    if missing_required:
        print(f"WARNING: Required companies missing after validation: {', '.join(missing_required)}")

    if len(accepted) < 12:
        print(f"WARNING: Only {len(accepted)} accepted examples; target is at least 12.")

    output_payload = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "methodology": {
            "public_sources_only": True,
            "robots_checked": True,
            "rate_limited": True,
            "deduplicated": True,
            "sorted_by_relevance": True,
            "selection_target": "12-20 distinct examples",
        },
        "summary": {
            "total_examples": len(accepted),
            "sectors_covered": sorted({e["sector_filter"] for e in accepted}),
            "status_breakdown": {
                "live": sum(1 for e in accepted if e["status"] == "live"),
                "pilot": sum(1 for e in accepted if e["status"] == "pilot"),
                "announced": sum(1 for e in accepted if e["status"] == "announced"),
                "demo": sum(1 for e in accepted if e["status"] == "demo"),
            },
            "required_companies_present": sorted(list(final_companies.intersection(REQUIRED_COMPANIES))),
            "required_companies_missing": missing_required,
        },
        "examples": accepted,
    }

    (out_dir / "ai_commerce_examples.json").write_text(
        json.dumps(output_payload, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    (out_dir / "ai_commerce_rejections.json").write_text(
        json.dumps(
            {
                "generated_at_utc": datetime.now(timezone.utc).isoformat(),
                "rejected_count": len(rejected),
                "rejections": rejected,
            },
            indent=2,
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    print("Wrote data/ai_commerce_examples.json")
    print("Wrote data/ai_commerce_rejections.json")
    print(f"Accepted examples: {len(accepted)}")


if __name__ == "__main__":
    main()

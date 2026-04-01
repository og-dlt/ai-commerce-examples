#!/usr/bin/env bash
set -euo pipefail

USER_AGENT="AgentCommerceResearchBot/1.0 (public research; respectful crawling)"
DELAY_SECONDS=4
OUT_FILE="data/examples.json"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p data

# format: organization|region|category|url|terms_url|org_home
SOURCES=(
  "Billshark|US|telco|https://www.billshark.com/|https://www.billshark.com/terms-of-service|https://www.billshark.com/"
  "Rocket Money|US|telco|https://www.rocketmoney.com/features/bill-negotiation|https://www.rocketmoney.com/terms|https://www.rocketmoney.com/"
  "Pine AI|US|utilities|https://www.19pine.ai/feature/lower-your-bills/|https://www.19pine.ai/terms|https://www.19pine.ai/"
  "DoNotPay|US|telco|https://donotpay.com/learn/lower-cable-bill/|https://donotpay.com/terms|https://donotpay.com/"
  "Trim|US|telco|https://www.asktrim.com/how-it-works/|https://www.asktrim.com/terms|https://www.asktrim.com/"
  "Hiatus|US|utilities|https://www.hiatus.com/|https://www.hiatus.com/terms|https://www.hiatus.com/"
  "Klarna|US/EU|retail|https://www.klarna.com/us/blog/our-ai-assistant-is-here/|https://www.klarna.com/us/terms-and-conditions/|https://www.klarna.com/"
  "Microsoft Copilot Shopping Deals|US/EU|retail|https://www.microsoft.com/en-us/microsoft-copilot/for-individuals/do-more-with-ai/general-ai/find-online-deals-with-copilot-shopping|https://www.microsoft.com/en-us/servicesagreement|https://www.microsoft.com/"
  "Microsoft Copilot Shopping Assistant|US/EU|retail|https://www.microsoft.com/en-us/microsoft-copilot/for-individuals/do-more-with-ai/ai-for-daily-life/shop-smarter-with-an-ai-shopping-assistant|https://www.microsoft.com/en-us/servicesagreement|https://www.microsoft.com/"
  "Google Shopping AI Update|US/EU|retail|https://blog.google/products/shopping/google-shopping-ai-update-october-2024|https://policies.google.com/terms|https://blog.google/"
  "Google Shopping Best Prices|US/EU|retail|https://www.blog.google/products/shopping/find-best-prices-and-places-buy-google-shopping/|https://policies.google.com/terms|https://blog.google/"
  "Amazon Rufus Help|US/EU|retail|https://www.amazon.com/gp/help/customer/display.html?nodeId=Tvh55TTsQ5XQSFc7Pr|https://www.amazon.com/gp/help/customer/display.html?nodeId=508088|https://www.amazon.com/"
  "Amazon Auto Buy|US/EU|retail|https://www.amazon.com/gp/help/customer/display.html?nodeId=TsaUdPSIWqy1tZhF09|https://www.amazon.com/gp/help/customer/display.html?nodeId=508088|https://www.amazon.com/"
  "Meta Shopping AI|US/EU|retail|https://about.fb.com/news/2021/06/advancing-ai-to-make-shopping-easier-for-everyone/|https://www.facebook.com/legal/terms|https://about.fb.com/"
  "Meta Marketplace AI Tools|US/EU|retail|https://about.fb.com/news/2026/03/facebook-marketplace-new-meta-ai-tools-make-selling-faster-and-easier/|https://www.facebook.com/legal/terms|https://about.fb.com/"
  "Perplexity Shop Like a Pro|US/EU|retail|https://www.perplexity.ai/hub/blog/shop-like-a-pro|https://www.perplexity.ai/hub/legal/terms-of-service|https://www.perplexity.ai/"
  "OpenAI Shopping in ChatGPT|US/EU|retail|https://openai.com/index/introducing-chatgpt-search/|https://openai.com/policies/terms-of-use/|https://openai.com/"
  "Priceline Penny|US/EU|travel|https://www.priceline.com/partner-network/press-release/priceline-introduces-penny-voice-assistant/|https://www.priceline.com/static-pages/terms-and-conditions|https://www.priceline.com/"
  "Expedia ChatGPT Planning|US/EU|travel|https://expediagroup.com/investors/news-and-events/financial-releases/news/news-details/2023/Chatgpt-Wrote-This-Press-Release--No-It-Didnt-But-It-Can-Now-Assist-With-Travel-Planning-In-The-Expedia-App/default.aspx|https://www.expediagroup.com/who-we-are/legal/default.aspx|https://www.expediagroup.com/"
  "KAYAK AI Lab|US/EU|travel|https://www.kayak.com/news/introducing-kayak-ai/|https://www.kayak.com/terms|https://www.kayak.com/"
  "KAYAK AI Mode|US/EU|travel|https://www.kayak.com/news/ai-mode/|https://www.kayak.com/terms|https://www.kayak.com/"
  "Skyscanner AI Trip Planner|EU|travel|https://www.skyscanner.net/news/introducing-skyscanner-ai-trip-planner|https://www.skyscanner.net/terms-and-conditions|https://www.skyscanner.net/"
  "Comparor AI Assistant|US/EU|retail|https://finance.yahoo.com/news/comparor-launches-ai-shopping-assistant-121600135.html|https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html|https://finance.yahoo.com/"
  "Goji Mobile ChatBarry|EU|telco|https://www.gojimobile.com/blog/meet-chatbarry|https://www.gojimobile.com/terms-conditions|https://www.gojimobile.com/"
  "Instacart|US|retail|https://www.instacart.com/company/updates/introducing-ask-instacart/|https://www.instacart.com/help/section/360007996832|https://www.instacart.com/"
)

robots_allows() {
  local url="$1"
  local origin path robots_url robots_txt disallow_match
  origin="$(printf "%s" "$url" | awk -F/ '{print $1"//"$3}')"
  path="/$(printf "%s" "$url" | awk -F/ '{for (i=4; i<=NF; i++) printf("%s%s", $i, (i<NF?"/":""))}')"
  robots_url="$origin/robots.txt"

  if ! robots_txt="$(curl -sS -L --compressed -m 15 -A "$USER_AGENT" "$robots_url" 2>/dev/null)"; then
    return 1
  fi

  # Parse only User-agent: * block(s), collecting Disallow paths.
  disallow_match="$(
    printf "%s" "$robots_txt" | awk -v p="$path" '
      BEGIN { in_star=0; blocked=0; }
      /^[[:space:]]*#/ { next }
      tolower($1)=="user-agent:" {
        in_star = (tolower($2)=="*")
        next
      }
      in_star && tolower($1)=="disallow:" {
        rule=$2
        if (rule=="" || rule=="/") {
          if (rule=="/") blocked=1
          next
        }
        if (index(p, rule)==1) blocked=1
      }
      END { print blocked }'
  )"

  [[ "$disallow_match" == "0" ]]
}

extract_text() {
  local html_file="$1"
  perl -0777 -pe 's/<script\b[^>]*>.*?<\/script>/ /gis; s/<style\b[^>]*>.*?<\/style>/ /gis; s/<[^>]+>/ /g; s/[^\x09\x0A\x0D\x20-\x7E]/ /g; s/\s+/ /g;' "$html_file"
}

extract_title() {
  local html_file="$1"
  perl -0777 -ne 'if (/<title[^>]*>(.*?)<\/title>/is) { $t=$1; $t =~ s/<[^>]+>/ /g; $t =~ s/\s+/ /g; $t =~ s/^\s+|\s+$//g; print $t; }' "$html_file"
}

extract_evidence() {
  local text="$1"
  printf "%s" "$text" | awk 'BEGIN{RS="[.!?] "; IGNORECASE=1}
    /agent|assistant|ai|compare|shop|buy|purchase|negotiate|carrier|retailer|provider|cable|plan|best price|best deal/ {
      gsub(/\n/," ");
      if (length($0) > 40) { print $0 "."; exit }
    }'
}

declare -a json_items=()
for src in "${SOURCES[@]}"; do
  IFS="|" read -r organization region category url terms_url org_home <<< "$src"

  if ! robots_allows "$url"; then
    echo "Skipping (robots disallow/unavailable): $organization"
    continue
  fi

  html_file="$TMP_DIR/page.html"
  if ! curl -sS -L --compressed -m 25 -A "$USER_AGENT" "$url" -o "$html_file"; then
    echo "Skipping (fetch failed): $organization"
    continue
  fi

  title="$(extract_title "$html_file")"
  text="$(extract_text "$html_file")"
  evidence="$(extract_evidence "$text")"
  summary="$(printf "%s" "$text" | awk '{print substr($0,1,420)}')"

  if printf "%s %s" "$title" "$summary" | awk 'BEGIN{IGNORECASE=1} /404|page not found|this page doesn.t exist|oops, something went wrong/ {exit 0} {exit 1}'; then
    echo "Skipping (error page): $organization"
    sleep "$DELAY_SECONDS"
    continue
  fi

  if [[ -z "$evidence" ]]; then
    echo "Skipping (no agentic-commerce signal): $organization"
    sleep "$DELAY_SECONDS"
    continue
  fi

  item="$(
    jq -n \
      --arg organization "$organization" \
      --arg organization_home "$org_home" \
      --arg source_url "$url" \
      --arg source_title "$title" \
      --arg terms_url "$terms_url" \
      --arg region "$region" \
      --arg category "$category" \
      --arg summary "$summary" \
      --arg evidence_snippet "$evidence" \
      --arg scraped_at_utc "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
      '{
        organization: $organization,
        organization_home: $organization_home,
        source_url: $source_url,
        source_title: $source_title,
        terms_url: $terms_url,
        region: $region,
        category: $category,
        summary: $summary,
        evidence_snippet: $evidence_snippet,
        compliance: {
          public_page: true,
          robots_checked: true,
          terms_review_note: "Publicly accessible page; confirm legal interpretation manually."
        },
        scraped_at_utc: $scraped_at_utc
      }'
  )"

  json_items+=("$item")
  echo "Collected: $organization"
  sleep "$DELAY_SECONDS"
done

if [[ "${#json_items[@]}" -eq 0 ]]; then
  jq -n \
    --arg now "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
    '{
      generated_at_utc: $now,
      count: 0,
      query: "Public examples of agents that buy/compare/negotiate for consumers in US/Europe.",
      examples: []
    }' > "$OUT_FILE"
else
  {
    printf '%s\n' "${json_items[@]}" | jq -s \
      --arg now "$(date -u +"%Y-%m-%dT%H:%M:%SZ")" \
      '{
        generated_at_utc: $now,
        count: length,
        query: "Public examples of agents that buy/compare/negotiate for consumers in US/Europe.",
        examples: .
      }'
  } > "$OUT_FILE"
fi

echo "Saved to $OUT_FILE"

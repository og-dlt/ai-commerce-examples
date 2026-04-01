# Agentic Commerce Example Scraper

Small, local project to collect public examples of agents that help consumers compare, buy, or negotiate products/services (with focus on telco + retail in US/Europe).

## What this project includes

- `scrape_examples.sh`: runnable scraper (no external dependencies beyond `curl`, `jq`, `perl`, `awk`).
- `scrape_examples.py`: optional standard-library Python version.
- `data/examples.json`: extracted output.
- `report.html`: local HTML report that reads `./data/examples.json`.

## Compliance behavior

- Uses only publicly accessible URLs.
- Checks `robots.txt` before fetching target pages.
- Adds polite delay between requests (`DELAY_SECONDS=4`).
- Stores a terms URL per source for manual policy review.

## Run

```bash
./scrape_examples.sh
```

Then serve locally and open the report:

```bash
python3 -m http.server
```

Open: `http://localhost:8000/report.html`

## Output schema

`data/examples.json` contains:

- `generated_at_utc`
- `count`
- `query`
- `examples[]` with:
  - `organization`, `organization_home`
  - `source_url`, `source_title`, `terms_url`
  - `region`, `category`
  - `summary`, `evidence_snippet`
  - `compliance`
  - `scraped_at_utc`

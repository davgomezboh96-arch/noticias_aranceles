# noticias_aranceles

Daily scraper that collects tariff and trade war news from major RSS feeds,
filters articles from the last 48 hours by keyword, and generates a Markdown report.
Runs automatically every day at 7:00 AM via cron.

---

## Sources

| Source | Language |
|---|---|
| Reuters Business | English |
| BBC Mundo | Spanish |
| El País Economía | Spanish |
| CNBC Economy | English |
| CNN Business | English |
| Al Jazeera | English |

---

## Keywords monitored

**Spanish:** arancel, aranceles, proteccionismo, guerra comercial, tarifas aduaneras, barreras comerciales, libre comercio

**English:** tariff, tariffs, trade war, protectionism, customs duties, import tax, export tax, trade barriers, trade deal, trade agreement, trade dispute, trade policy, WTO, USMCA, trade restriction, trade sanction

---

## Setup

```bash
# 1. Install dependencies
bash setup.sh

# 2. Run once to verify
python3 noticias_aranceles.py

# 3. Install daily cron job (7:00 AM)
bash install_cron.sh
```

---

## Output

Each run generates a Markdown file in `output/`:

```
output/aranceles_YYYY-MM-DD.md
```

Example:

```markdown
# Tariff & Trade War News

**Generated:** Monday, March 09, 2026 at 07:00 UTC
**Period:** Last 48 hours
**Total articles:** 12

---

## Reuters Business (5 articles)

### [US raises tariffs on Chinese goods](https://reuters.com/...)
*Mar 09, 06:30 UTC*

The United States announced new tariffs on a range of Chinese imports...
```

Logs are saved in `logs/` — one file per run plus a persistent `cron.log` for scheduled runs.

---

## Customization

All configuration is at the top of `noticias_aranceles.py`:

| Variable | Default | Description |
|---|---|---|
| `FEEDS` | 6 sources | Add or remove RSS feed URLs |
| `KEYWORDS` | 25 terms | Add or remove filter keywords |
| `HOURS_BACK` | `48` | How far back to look for articles |
| `MAX_RETRIES` | `2` | Retries per feed on failure |

---

## Project structure

```
noticias_aranceles/
├── noticias_aranceles.py   # Main scraper
├── setup.sh                # Install dependencies and create directories
├── install_cron.sh         # Install daily cron job
├── requirements.txt        # Python dependencies (feedparser)
├── output/                 # Generated Markdown reports (git-ignored)
└── logs/                   # Execution logs (git-ignored)
```

---

## Useful cron commands

```bash
crontab -l          # View your cron jobs
crontab -e          # Edit your cron jobs
tail -f logs/cron.log  # Follow the scheduled run log
```

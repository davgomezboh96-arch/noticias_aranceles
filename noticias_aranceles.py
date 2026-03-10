#!/usr/bin/env python3
"""
noticias_aranceles.py — Daily tariff & trade war news scraper.

Connects to RSS feeds from major news sources, filters articles
mentioning tariffs and trade-related topics from the last 48 hours,
and generates a Markdown report in the output/ directory.

Author: David Gomez
"""

import feedparser
import logging
import os
import smtplib
import time
from datetime import datetime, timezone, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

FEEDS = {
    "Reuters Business":   "https://feeds.reuters.com/reuters/businessNews",
    "BBC Mundo":          "https://feeds.bbci.co.uk/mundo/rss.xml",
    "El País Economía":   "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/economia/portada",
    "CNBC Economy":       "https://www.cnbc.com/id/20910258/device/rss/rss.html",
    "CNN Business":       "http://rss.cnn.com/rss/money_news_international.rss",
    "Al Jazeera":         "https://www.aljazeera.com/xml/rss/all.xml",
}

# Keywords to match against title + summary (case-insensitive)
KEYWORDS = [
    # Spanish
    "arancel", "aranceles", "proteccionismo", "guerra comercial",
    "tarifas aduaneras", "barreras comerciales", "libre comercio",
    "impuesto a las importaciones", "impuesto a las exportaciones",
    # English
    "tariff", "tariffs", "trade war", "protectionism", "customs duty",
    "customs duties", "import tax", "export tax", "trade barrier",
    "trade barriers", "trade deal", "trade agreement", "trade dispute",
    "trade policy", "import duty", "export duty", "WTO", "USMCA",
    "trade restriction", "trade sanction",
]

HOURS_BACK      = 48   # How many hours back to look for articles
REQUEST_TIMEOUT = 10   # Seconds before giving up on a feed
MAX_RETRIES     = 2    # Retries per feed on failure

BASE_DIR   = Path(__file__).parent
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR    = BASE_DIR / "logs"

# ---------------------------------------------------------------------------
# Email configuration — set these in your .env file
# ---------------------------------------------------------------------------
EMAIL_SENDER    = os.environ.get("EMAIL_SENDER", "")       # your Gmail address
EMAIL_PASSWORD  = os.environ.get("EMAIL_PASSWORD", "")     # Gmail App Password (16 chars)
EMAIL_RECIPIENT = os.environ.get("EMAIL_RECIPIENT", "")    # destination address


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def setup_logging() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    logger = logging.getLogger("noticias_aranceles")
    logger.setLevel(logging.DEBUG)

    # Avoid duplicate handlers if module is re-imported
    if logger.handlers:
        return logger

    stream = logging.StreamHandler()
    stream.setLevel(logging.INFO)
    stream.setFormatter(fmt)

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(fmt)

    logger.addHandler(stream)
    logger.addHandler(fh)
    return logger


# ---------------------------------------------------------------------------
# Feed fetching
# ---------------------------------------------------------------------------

def fetch_feed(source: str, url: str, logger: logging.Logger) -> list[dict]:
    """
    Fetches a single RSS feed with retry logic.
    A failed feed is logged and skipped — it never stops the rest of the run.
    Returns a list of filtered article dicts.
    """
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.debug(f"Fetching {source} (attempt {attempt})...")
            feed = feedparser.parse(
                url,
                request_headers={"User-Agent": "Mozilla/5.0"},
            )

            # feedparser sets bozo=True when the feed is malformed but may
            # still return entries — we only raise if there are no entries at all.
            if feed.bozo and not feed.entries:
                raise ValueError(f"Malformed feed: {feed.bozo_exception}")

            articles = [
                _extract(entry)
                for entry in feed.entries
                if _is_recent(entry) and _is_relevant(entry)
            ]

            logger.info(f"{source}: {len(articles)} relevant article(s) found.")
            return articles

        except Exception as e:
            logger.warning(f"{source} — attempt {attempt} failed: {e}")
            if attempt < MAX_RETRIES:
                time.sleep(2)

    logger.error(f"{source}: all retries exhausted. Skipping.")
    return []


def _extract(entry) -> dict:
    return {
        "title":   entry.get("title", "(no title)").strip(),
        "link":    entry.get("link", ""),
        "summary": entry.get("summary", entry.get("description", "")).strip(),
        "date":    _parse_date(entry),
    }


def _parse_date(entry) -> datetime | None:
    """Converts feed time struct to a timezone-aware datetime."""
    for field in ("published_parsed", "updated_parsed"):
        t = entry.get(field)
        if t:
            try:
                return datetime(*t[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def _is_recent(entry, hours: int = HOURS_BACK) -> bool:
    """True if the article was published within the last N hours.
    Articles with no parseable date are included to avoid false negatives."""
    dt = _parse_date(entry)
    if dt is None:
        return True
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return dt >= cutoff


def _is_relevant(entry) -> bool:
    """True if any keyword appears in the article's title or summary."""
    text = " ".join([
        entry.get("title", ""),
        entry.get("summary", ""),
        entry.get("description", ""),
    ]).lower()
    return any(kw.lower() in text for kw in KEYWORDS)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_markdown(results: dict[str, list[dict]], run_date: datetime) -> str:
    """Builds the Markdown report from the collected articles."""
    total = sum(len(v) for v in results.values())

    lines = [
        "# Tariff & Trade War News",
        "",
        f"**Generated:** {run_date.strftime('%A, %B %d, %Y at %H:%M UTC')}  ",
        f"**Period:** Last {HOURS_BACK} hours  ",
        f"**Total articles:** {total}",
        "",
        "---",
        "",
    ]

    if total == 0:
        lines.append("*No relevant articles found in the last 48 hours.*")
        return "\n".join(lines)

    for source, articles in results.items():
        if not articles:
            continue

        lines.append(f"## {source} ({len(articles)} article(s))")
        lines.append("")

        # Sort by date descending (most recent first)
        sorted_articles = sorted(
            articles,
            key=lambda a: a["date"] or datetime.min.replace(tzinfo=timezone.utc),
            reverse=True,
        )

        for art in sorted_articles:
            date_str = art["date"].strftime("%b %d, %H:%M UTC") if art["date"] else "Unknown date"
            summary  = art["summary"][:350].strip() if art["summary"] else ""
            if summary and not summary.endswith((".", "!", "?")):
                summary += "..."

            lines.append(f"### [{art['title']}]({art['link']})")
            lines.append(f"*{date_str}*")
            lines.append("")
            if summary:
                lines.append(summary)
                lines.append("")

        lines.append("---")
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Email sending
# ---------------------------------------------------------------------------

def send_email(md_content: str, total: int, run_date: datetime, logger: logging.Logger) -> None:
    """
    Sends the report as an HTML email via Gmail SMTP (TLS, port 587).
    Reads credentials from EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT in .env.
    """
    if not all([EMAIL_SENDER, EMAIL_PASSWORD, EMAIL_RECIPIENT]):
        logger.warning("Email credentials not configured in .env — skipping send.")
        return

    subject = f"Tariff News — {run_date.strftime('%B %d, %Y')} ({total} article{'s' if total != 1 else ''})"
    html_body = _md_to_html(md_content, run_date, total)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_SENDER
    msg["To"]      = EMAIL_RECIPIENT
    msg.attach(MIMEText(md_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_body,  "html",  "utf-8"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECIPIENT, msg.as_string())
    except smtplib.SMTPAuthenticationError as e:
        logger.error(f"Authentication failed — check App Password in .env: {e}")
        raise
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error: {e}")
        raise
    except OSError as e:
        logger.error(f"Network error (port 587 blocked?): {e}")
        raise

    logger.info(f"Email sent to {EMAIL_RECIPIENT}")


def _md_to_html(md: str, run_date: datetime, total: int) -> str:
    """Converts the Markdown report to a simple styled HTML email body."""
    css = """
    <style>
      body  { font-family: Segoe UI, Arial, sans-serif; font-size: 14px;
              color: #222; max-width: 800px; margin: 0 auto; padding: 20px; }
      h1    { color: #C00000; font-size: 20px; }
      h2    { color: #2F5496; font-size: 15px; border-bottom: 1px solid #2F5496;
              padding-bottom: 4px; margin-top: 28px; }
      h3    { font-size: 14px; margin-bottom: 2px; }
      h3 a  { color: #1a0dab; text-decoration: none; }
      h3 a:hover { text-decoration: underline; }
      em    { color: #888; font-size: 12px; }
      p     { margin: 4px 0 12px; }
      hr    { border: none; border-top: 1px solid #ddd; margin: 16px 0; }
      .meta { background: #f0f4ff; border-left: 4px solid #2F5496;
              padding: 10px 16px; margin-bottom: 16px; font-size: 13px; }
    </style>"""

    lines = md.splitlines()
    html_lines = [f"<!DOCTYPE html><html><head><meta charset='utf-8'>{css}</head><body>"]

    for line in lines:
        if line.startswith("# "):
            html_lines.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html_lines.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            # Convert [title](url) to <a href>
            inner = line[4:]
            if inner.startswith("[") and "](" in inner:
                title = inner[1:inner.index("]")]
                url   = inner[inner.index("](") + 2 : inner.rindex(")")]
                html_lines.append(f"<h3><a href='{url}'>{title}</a></h3>")
            else:
                html_lines.append(f"<h3>{inner}</h3>")
        elif line.startswith("**") and line.endswith("**"):
            html_lines.append(f"<div class='meta'>{line}</div>")
        elif line.startswith("*") and line.endswith("*") and not line.startswith("**"):
            html_lines.append(f"<em>{line.strip('*')}</em><br>")
        elif line.strip() == "---":
            html_lines.append("<hr>")
        elif line.strip():
            html_lines.append(f"<p>{line}</p>")

    html_lines.append("</body></html>")
    return "\n".join(html_lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    logger = setup_logging()
    logger.info("=== Tariff news scraper started ===")

    OUTPUT_DIR.mkdir(exist_ok=True)
    run_date = datetime.now(timezone.utc)

    # Fetch all feeds — each one is independent; failures don't stop the loop
    results = {source: fetch_feed(source, url, logger) for source, url in FEEDS.items()}

    total = sum(len(v) for v in results.values())
    logger.info(f"Total relevant articles collected: {total}")

    md_content = generate_markdown(results, run_date)

    output_file = OUTPUT_DIR / f"aranceles_{run_date.strftime('%Y-%m-%d')}.md"
    output_file.write_text(md_content, encoding="utf-8")
    logger.info(f"Report saved: {output_file}")

    send_email(md_content, total, run_date, logger)
    logger.info("=== Scraper complete ===")


if __name__ == "__main__":
    main()

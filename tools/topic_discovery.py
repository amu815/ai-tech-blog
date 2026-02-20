#!/usr/bin/env python3
"""
Topic Discovery - Fetch RSS feeds, score entries, and suggest trending topics.

Usage:
  python topic_discovery.py              # Discover top 3 topics
  python topic_discovery.py --count 5    # Discover top 5 topics
  python topic_discovery.py --dump       # Dump all scored entries
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("Error: feedparser not installed. Run: pip install --user feedparser", file=sys.stderr)
    sys.exit(1)

TOOLS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = TOOLS_DIR / "config"
FEEDS_CONFIG = CONFIG_DIR / "feeds.json"
HISTORY_FILE = CONFIG_DIR / "topics_history.json"
BLOG_ROOT = TOOLS_DIR.parent
CONTENT_DIR = BLOG_ROOT / "content"

JST = timezone(timedelta(hours=9))

CATEGORY_KEYWORDS = {
    "ai": ["llm", "gpt", "transformer", "machine learning", "deep learning",
           "neural", "ai", "fine-tuning", "rag", "embedding", "prompt",
           "diffusion", "generative", "chatbot", "copilot", "langchain",
           "openai", "anthropic", "claude", "gemini", "llama", "mistral"],
    "tech": ["docker", "kubernetes", "python", "rust", "typescript", "devops",
             "cloud", "api", "database", "microservices", "cicd", "linux",
             "security", "wasm", "edge", "serverless", "terraform"],
    "research": ["arxiv", "paper", "benchmark", "dataset", "model", "training",
                 "inference", "scaling", "alignment", "evaluation", "survey",
                 "attention", "reasoning", "multimodal"],
}


def load_feeds_config() -> dict:
    """Load RSS feed configuration."""
    with open(FEEDS_CONFIG, encoding="utf-8") as f:
        return json.load(f)


def load_history() -> list[dict]:
    """Load previously generated topic history."""
    if not HISTORY_FILE.exists():
        return []
    with open(HISTORY_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data.get("generated", [])


def save_history(history: list[dict]) -> None:
    """Save topic history."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump({"generated": history}, f, ensure_ascii=False, indent=2)


def get_existing_slugs() -> set[str]:
    """Get slugs of all existing articles to avoid duplicates."""
    slugs = set()
    for md_file in CONTENT_DIR.rglob("*.md"):
        slugs.add(md_file.stem.lower())
        # Also extract slug from front matter
        try:
            text = md_file.read_text(encoding="utf-8")
            m = re.search(r'^slug:\s*"?([^"\n]+)"?', text, re.MULTILINE)
            if m:
                slugs.add(m.group(1).strip().lower())
        except Exception:
            pass
    return slugs


def classify_category(text: str) -> str:
    """Classify an entry into a category based on keyword matching."""
    text_lower = text.lower()
    scores = {}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in text_lower)
        scores[cat] = score
    best = max(scores, key=scores.get)
    return best if scores[best] > 0 else "tech"


def compute_keyword_score(text: str, category: str) -> float:
    """Score how relevant an entry is based on keyword matches."""
    text_lower = text.lower()
    keywords = CATEGORY_KEYWORDS.get(category, [])
    if not keywords:
        return 0.0
    matches = sum(1 for kw in keywords if kw in text_lower)
    return min(matches / 3.0, 1.0)  # Normalize: 3+ matches = 1.0


def compute_recency_score(published: datetime | None) -> float:
    """Score based on how recent the entry is (0-1, 1 = today)."""
    if not published:
        return 0.5  # Unknown date gets mid score
    now = datetime.now(tz=timezone.utc)
    age_hours = (now - published).total_seconds() / 3600
    if age_hours < 6:
        return 1.0
    elif age_hours < 24:
        return 0.8
    elif age_hours < 72:
        return 0.5
    elif age_hours < 168:
        return 0.3
    return 0.1


def parse_entry_date(entry) -> datetime | None:
    """Extract publication date from a feed entry."""
    for attr in ("published_parsed", "updated_parsed"):
        parsed = getattr(entry, attr, None)
        if parsed:
            try:
                return datetime(*parsed[:6], tzinfo=timezone.utc)
            except Exception:
                pass
    return None


def extract_topic_keyword(entry) -> str:
    """Extract a concise keyword/topic from a feed entry title."""
    title = entry.get("title", "").strip()
    # Remove common prefixes like "[D]", "Show HN:", etc.
    title = re.sub(r'^\[.*?\]\s*', '', title)
    title = re.sub(r'^Show HN:\s*', '', title, flags=re.IGNORECASE)
    title = re.sub(r'^Ask HN:\s*', '', title, flags=re.IGNORECASE)
    # Truncate very long titles
    if len(title) > 80:
        title = title[:77] + "..."
    return title


def fetch_feed(feed_config: dict) -> list[dict]:
    """Fetch and parse a single RSS feed, return scored entries."""
    name = feed_config["name"]
    url = feed_config["url"]
    default_lang = feed_config["language"]
    default_cat = feed_config["category"]
    weight = feed_config.get("weight", 1.0)

    print(f"  Fetching: {name} ...", file=sys.stderr)
    try:
        feed = feedparser.parse(url)
    except Exception as e:
        print(f"  Failed to fetch {name}: {e}", file=sys.stderr)
        return []

    if feed.bozo and not feed.entries:
        print(f"  Warning: {name} returned no entries (bozo={feed.bozo_exception})", file=sys.stderr)
        return []

    entries = []
    for entry in feed.entries[:20]:  # Limit to 20 most recent
        title = entry.get("title", "")
        summary = entry.get("summary", "")
        combined_text = f"{title} {summary}"
        keyword = extract_topic_keyword(entry)
        category = classify_category(combined_text)

        # If the feed has a default category and the classification is weak, use default
        if category == "tech" and default_cat != "tech":
            category = default_cat

        pub_date = parse_entry_date(entry)
        kw_score = compute_keyword_score(combined_text, category)
        recency = compute_recency_score(pub_date)
        total_score = (0.7 * kw_score + 0.3 * recency) * weight

        source_url = entry.get("link", "")

        entries.append({
            "keyword": keyword,
            "lang": default_lang,
            "category": category,
            "score": round(total_score, 3),
            "source_url": source_url,
            "source_feed": name,
            "published": pub_date.isoformat() if pub_date else None,
        })

    return entries


def deduplicate(topics: list[dict], existing_slugs: set[str],
                history: list[dict], dedup_days: int = 7) -> list[dict]:
    """Remove topics that are duplicates of existing articles or recent history."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=dedup_days)

    # Build set of recently generated keywords
    recent_keywords = set()
    for h in history:
        try:
            gen_date = datetime.fromisoformat(h["date"])
            if gen_date.tzinfo is None:
                gen_date = gen_date.replace(tzinfo=timezone.utc)
            if gen_date > cutoff:
                recent_keywords.add(h["keyword"].lower())
        except (KeyError, ValueError):
            pass

    seen_keywords = set()
    result = []
    for topic in topics:
        kw_lower = topic["keyword"].lower()
        # Check against existing article slugs
        slug = re.sub(r"[^\w\s-]", "", kw_lower)
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        if slug in existing_slugs:
            continue
        # Check against recent history
        if kw_lower in recent_keywords:
            continue
        # Check against duplicates in current batch
        if kw_lower in seen_keywords:
            continue
        seen_keywords.add(kw_lower)
        result.append(topic)

    return result


def balance_languages(topics: list[dict], ja_ratio: int = 60,
                      max_count: int = 3) -> list[dict]:
    """Balance topic selection by language ratio."""
    ja_target = max(1, round(max_count * ja_ratio / 100))
    en_target = max_count - ja_target

    ja_topics = [t for t in topics if t["lang"] == "ja"]
    en_topics = [t for t in topics if t["lang"] == "en"]

    selected = ja_topics[:ja_target] + en_topics[:en_target]

    # Fill remaining slots from whichever has more
    remaining = max_count - len(selected)
    if remaining > 0:
        all_remaining = [t for t in topics if t not in selected]
        selected.extend(all_remaining[:remaining])

    return selected[:max_count]


def discover_topics(count: int = 3, dump: bool = False) -> list[dict]:
    """Main discovery pipeline: fetch → score → dedup → balance → select."""
    config = load_feeds_config()
    settings = config.get("settings", {})
    dedup_days = settings.get("dedup_window_days", 7)
    ja_ratio = settings.get("ja_en_ratio", [60, 40])[0]
    min_score = settings.get("min_score", 0.3)

    # Fetch all feeds
    all_entries = []
    for feed_config in config["feeds"]:
        entries = fetch_feed(feed_config)
        all_entries.extend(entries)
        time.sleep(1)  # Rate limiting between feeds

    if not all_entries:
        print("No entries found from any feed.", file=sys.stderr)
        return []

    # Sort by score descending
    all_entries.sort(key=lambda x: x["score"], reverse=True)

    if dump:
        for entry in all_entries[:30]:
            print(f"  [{entry['score']:.3f}] [{entry['lang']}] [{entry['category']}] "
                  f"{entry['keyword']} ({entry['source_feed']})")
        return all_entries

    # Filter by minimum score
    filtered = [e for e in all_entries if e["score"] >= min_score]
    if not filtered:
        print(f"No entries above minimum score ({min_score}). Using top entries.", file=sys.stderr)
        filtered = all_entries[:count * 3]

    # Deduplicate
    existing_slugs = get_existing_slugs()
    history = load_history()
    deduped = deduplicate(filtered, existing_slugs, history, dedup_days)

    # Balance languages and select top topics
    selected = balance_languages(deduped, ja_ratio, count)

    # Record in history
    now = datetime.now(tz=JST).isoformat()
    for topic in selected:
        history.append({
            "keyword": topic["keyword"],
            "lang": topic["lang"],
            "category": topic["category"],
            "date": now,
        })
    save_history(history)

    return selected


def main():
    parser = argparse.ArgumentParser(description="Discover trending topics from RSS feeds")
    parser.add_argument("--count", "-n", type=int, default=3, help="Number of topics to discover (default: 3)")
    parser.add_argument("--dump", action="store_true", help="Dump all scored entries (no dedup/selection)")
    args = parser.parse_args()

    print("Discovering trending topics...", file=sys.stderr)
    topics = discover_topics(count=args.count, dump=args.dump)

    if not args.dump:
        if topics:
            print(f"\nDiscovered {len(topics)} topics:", file=sys.stderr)
            for i, t in enumerate(topics, 1):
                print(f"  {i}. [{t['lang']}] [{t['category']}] {t['keyword']} "
                      f"(score: {t['score']:.3f}, source: {t['source_feed']})", file=sys.stderr)
            # Output JSON for piping to other tools
            print(json.dumps(topics, ensure_ascii=False, indent=2))
        else:
            print("No topics discovered.", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()

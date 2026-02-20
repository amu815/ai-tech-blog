#!/usr/bin/env python3
"""
Auto-Publish Orchestrator - Daily blog automation pipeline.

Workflow:
  1. Pre-warm Ollama
  2. Discover trending topics
  3. Generate 2 original articles
  4. Generate 1 summary article
  5. Git commit & push (triggers Cloudflare deploy)

Usage:
  python auto_publish.py              # Full pipeline
  python auto_publish.py --dry-run    # Discover + generate, skip git push
  python auto_publish.py --skip-push  # Generate but don't push
"""

import argparse
import json
import logging
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
BLOG_ROOT = TOOLS_DIR.parent
LOG_DIR = BLOG_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

JST = timezone(timedelta(hours=9))

# Add tools dir to path so we can import sibling modules
sys.path.insert(0, str(TOOLS_DIR))

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
DUCKDUCKGO_WAIT = 300  # 5 minutes between generations to avoid DDG rate limit


def setup_logging() -> logging.Logger:
    """Configure logging to both file and stderr."""
    logger = logging.getLogger("auto_publish")
    logger.setLevel(logging.INFO)

    # File handler
    log_file = LOG_DIR / "automation.log"
    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.INFO)
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    # Console handler
    ch = logging.StreamHandler(sys.stderr)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))

    logger.addHandler(fh)
    logger.addHandler(ch)
    return logger


def prewarm_ollama(logger: logging.Logger) -> bool:
    """Ping Ollama to ensure it's running and warm up the model."""
    logger.info("Pre-warming Ollama...")
    try:
        data = json.dumps({
            "model": "llama3.3:70b-instruct-q4_K_M",
            "prompt": "Hello",
            "stream": False,
            "options": {"num_predict": 1},
        }).encode()
        req = urllib.request.Request(
            OLLAMA_URL,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            resp.read()
        logger.info("Ollama is ready.")
        return True
    except Exception as e:
        logger.error(f"Ollama pre-warm failed: {e}")
        return False


def discover_topics(logger: logging.Logger, count: int = 3) -> list[dict]:
    """Run topic discovery and return selected topics."""
    logger.info(f"Discovering {count} trending topics...")
    from topic_discovery import discover_topics as _discover
    topics = _discover(count=count)
    if topics:
        for t in topics:
            logger.info(f"  Topic: [{t['lang']}] [{t['category']}] {t['keyword']} (score: {t['score']:.3f})")
    else:
        logger.warning("No topics discovered.")
    return topics


def generate_original_articles(logger: logging.Logger, topics: list[dict],
                                max_articles: int = 2) -> list[Path]:
    """Generate original articles from discovered topics."""
    from generate import generate_article
    generated = []
    selected = topics[:max_articles]

    for i, topic in enumerate(selected):
        keyword = topic["keyword"]
        lang = topic["lang"]
        category = topic["category"]

        logger.info(f"Generating article {i+1}/{len(selected)}: [{lang}] {keyword}")
        try:
            path = generate_article(keyword, lang, category)
            generated.append(path)
            logger.info(f"  Generated: {path.relative_to(BLOG_ROOT)}")
        except Exception as e:
            logger.error(f"  Failed to generate '{keyword}': {e}")

        # Wait between generations for DuckDuckGo rate limiting
        if i < len(selected) - 1:
            wait_time = DUCKDUCKGO_WAIT
            logger.info(f"  Waiting {wait_time}s for rate limit...")
            time.sleep(wait_time)

    return generated


def generate_summary_article(logger: logging.Logger, lang: str | None = None) -> list[Path]:
    """Generate a summary article from trending news."""
    from summarize_news import get_top_articles, generate_summary
    logger.info("Generating summary article...")

    articles = get_top_articles(count=1, lang=lang)
    if not articles:
        logger.warning("No articles found for summarization.")
        return []

    generated = []
    for article in articles:
        try:
            path = generate_summary(article)
            if path:
                generated.append(path)
                logger.info(f"  Summary saved: {path.relative_to(BLOG_ROOT)}")
        except Exception as e:
            logger.error(f"  Summary failed for '{article['title'][:50]}': {e}")

    return generated


def git_commit_and_push(logger: logging.Logger, paths: list[Path],
                         dry_run: bool = False) -> bool:
    """Stage, commit, and push generated articles."""
    if not paths:
        logger.info("No articles to commit.")
        return True

    # Stage files
    rel_paths = [str(p.relative_to(BLOG_ROOT)) for p in paths]
    logger.info(f"Staging {len(rel_paths)} files...")

    try:
        subprocess.run(
            ["git", "add"] + rel_paths,
            cwd=BLOG_ROOT, check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"git add failed: {e.stderr}")
        return False

    # Commit
    date_str = datetime.now(tz=JST).strftime("%Y-%m-%d")
    commit_msg = f"Auto-publish: {len(rel_paths)} articles ({date_str})"
    logger.info(f"Committing: {commit_msg}")

    if dry_run:
        logger.info("  [DRY RUN] Skipping commit and push.")
        # Unstage
        subprocess.run(["git", "reset", "HEAD"] + rel_paths,
                       cwd=BLOG_ROOT, capture_output=True)
        return True

    try:
        subprocess.run(
            ["git", "commit", "-m", commit_msg],
            cwd=BLOG_ROOT, check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as e:
        logger.error(f"git commit failed: {e.stderr}")
        return False

    # Push (with one retry)
    for attempt in range(2):
        try:
            logger.info(f"Pushing to remote (attempt {attempt + 1})...")
            subprocess.run(
                ["git", "push"],
                cwd=BLOG_ROOT, check=True, capture_output=True, text=True,
            )
            logger.info("Push successful. Cloudflare Pages will auto-deploy.")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"git push failed (attempt {attempt + 1}): {e.stderr}")
            if attempt == 0:
                time.sleep(5)

    logger.error("git push failed after 2 attempts.")
    return False


def run_pipeline(dry_run: bool = False, skip_push: bool = False) -> None:
    """Run the full auto-publish pipeline."""
    logger = setup_logging()
    start_time = time.time()

    logger.info("=" * 60)
    logger.info(f"Auto-publish pipeline started at {datetime.now(tz=JST).isoformat()}")
    logger.info("=" * 60)

    # Step 1: Pre-warm Ollama
    if not prewarm_ollama(logger):
        logger.error("Aborting: Ollama is not available.")
        return

    # Step 2: Discover topics
    topics = discover_topics(logger, count=3)
    if not topics:
        logger.error("Aborting: no topics discovered.")
        return

    all_generated: list[Path] = []

    # Step 3: Generate original articles (2)
    original_paths = generate_original_articles(logger, topics, max_articles=2)
    all_generated.extend(original_paths)

    # Wait before summary generation
    if original_paths:
        logger.info(f"Waiting {DUCKDUCKGO_WAIT}s before summary generation...")
        time.sleep(DUCKDUCKGO_WAIT)

    # Step 4: Generate summary article (1)
    # Alternate language: even days = ja, odd days = en
    day = datetime.now(tz=JST).day
    summary_lang = "ja" if day % 2 == 0 else "en"
    summary_paths = generate_summary_article(logger, lang=summary_lang)
    all_generated.extend(summary_paths)

    # Step 5: Git commit & push
    if all_generated and not skip_push:
        git_commit_and_push(logger, all_generated, dry_run=dry_run)
    elif skip_push:
        logger.info("Skipping git push (--skip-push).")
    else:
        logger.info("No articles generated, nothing to commit.")

    elapsed = time.time() - start_time
    logger.info(f"Pipeline completed in {elapsed/60:.1f} minutes.")
    logger.info(f"  Original articles: {len(original_paths)}")
    logger.info(f"  Summary articles: {len(summary_paths)}")
    logger.info(f"  Total generated: {len(all_generated)}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Auto-publish blog articles")
    parser.add_argument("--dry-run", action="store_true",
                        help="Run pipeline but skip git commit/push")
    parser.add_argument("--skip-push", action="store_true",
                        help="Generate articles but don't push to remote")
    args = parser.parse_args()

    run_pipeline(dry_run=args.dry_run, skip_push=args.skip_push)


if __name__ == "__main__":
    main()

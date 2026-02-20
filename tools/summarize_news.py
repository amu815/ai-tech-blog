#!/usr/bin/env python3
"""
News Summarizer - Fetch trending articles and create LLM-powered summaries.

Usage:
  python summarize_news.py                    # Generate 1 summary article
  python summarize_news.py --count 2          # Generate 2 summary articles
  python summarize_news.py --test             # Test with 1 article (no save)
  python summarize_news.py --lang ja          # Force Japanese summary
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Error: beautifulsoup4 not installed. Run: pip install --user beautifulsoup4", file=sys.stderr)
    sys.exit(1)

try:
    import feedparser
except ImportError:
    print("Error: feedparser not installed. Run: pip install --user feedparser", file=sys.stderr)
    sys.exit(1)

TOOLS_DIR = Path(__file__).resolve().parent
CONFIG_DIR = TOOLS_DIR / "config"
FEEDS_CONFIG = CONFIG_DIR / "feeds.json"
BLOG_ROOT = TOOLS_DIR.parent
CONTENT_DIR = BLOG_ROOT / "content"

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3.3:70b-instruct-q4_K_M"

JST = timezone(timedelta(hours=9))

SUMMARY_PROMPT_JA = """あなたはテクニカルライターです。以下の記事を日本語で要約し、ブログ記事として再構成してください。

元記事タイトル: {title}
元記事URL: {source_url}
元記事の内容:
{article_text}

以下のJSON形式で出力してください。JSONのみ返してください。
{{
  "title": "要約記事のタイトル（60文字以内）",
  "description": "メタディスクリプション（120文字以内）",
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],
  "body": "要約記事本文（マークダウン形式、## 見出しを3-4個使い、合計800-1200字）"
}}

要件:
- 元記事の要点を正確にまとめる
- 読者にとって有用な情報を優先する
- 自然な日本語で書く
- 自分の意見ではなく、元記事の内容を正確に伝える
- 最後に「出典」セクションを含め、元記事へのリンクを記載する
"""

SUMMARY_PROMPT_EN = """You are a technical writer. Summarize the following article and restructure it as a blog post.

Original article title: {title}
Original article URL: {source_url}
Article content:
{article_text}

Output ONLY in the following JSON format:
{{
  "title": "Summary article title (under 60 characters)",
  "description": "Meta description (under 160 characters)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "body": "Summary article body in Markdown, use 3-4 ## headings, 800-1200 words total"
}}

Requirements:
- Accurately summarize the key points of the original article
- Prioritize useful information for readers
- Write in natural, engaging English
- Convey the original article's content, not your own opinions
- Include a "Sources" section at the end with a link to the original article
"""


def fetch_article_text(url: str, max_chars: int = 5000) -> str:
    """Fetch article URL and extract main text content."""
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; BlogSummarizer/1.0)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            html = resp.read().decode("utf-8", errors="ignore")

        soup = BeautifulSoup(html, "html.parser")

        # Remove script, style, nav, header, footer elements
        for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form"]):
            tag.decompose()

        # Try to find main content area
        main = soup.find("article") or soup.find("main") or soup.find(class_=re.compile(r"(article|post|content|entry)"))
        if main:
            text = main.get_text(separator="\n", strip=True)
        else:
            text = soup.get_text(separator="\n", strip=True)

        # Clean up whitespace
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        text = "\n".join(lines)

        # Truncate to max_chars
        if len(text) > max_chars:
            text = text[:max_chars] + "\n[...truncated]"

        return text
    except Exception as e:
        print(f"  Failed to fetch article: {e}", file=sys.stderr)
        return ""


def call_ollama(prompt: str) -> str:
    """Call Ollama API for text generation."""
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 4096, "temperature": 0.5},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    with urllib.request.urlopen(req, timeout=600) as resp:
        result = json.loads(resp.read().decode())
        return result.get("response", "")


def extract_json(text: str) -> dict:
    """Extract article fields from LLM response using regex."""
    result = {}

    m = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if m:
        result["title"] = m.group(1)

    m = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if m:
        result["description"] = m.group(1)

    m = re.search(r'"tags"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if m:
        result["tags"] = re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))

    m = re.search(r'"body"\s*:\s*"', text)
    if m:
        body = text[m.end():]
        body = body.rstrip()
        if body.endswith("}"):
            body = body[:-1].rstrip()
        if body.endswith("}"):
            body = body[:-1].rstrip()
        if body.endswith('"'):
            body = body[:-1]
        body = body.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
        result["body"] = body

    if not result.get("title") and not result.get("body"):
        raise ValueError(f"Could not extract fields from response:\n{text[:500]}")

    return result


def get_top_articles(count: int = 2, lang: str | None = None) -> list[dict]:
    """Get top articles from RSS feeds for summarization."""
    with open(FEEDS_CONFIG, encoding="utf-8") as f:
        config = json.load(f)

    articles = []
    for feed_config in config["feeds"]:
        if lang and feed_config["language"] != lang:
            continue
        try:
            feed = feedparser.parse(feed_config["url"])
            for entry in feed.entries[:5]:
                link = entry.get("link", "")
                title = entry.get("title", "")
                if link and title:
                    articles.append({
                        "title": title,
                        "url": link,
                        "lang": feed_config["language"],
                        "category": feed_config["category"],
                        "feed": feed_config["name"],
                        "weight": feed_config.get("weight", 1.0),
                    })
        except Exception as e:
            print(f"  Feed error ({feed_config['name']}): {e}", file=sys.stderr)
        time.sleep(1)

    # Sort by weight (higher = better source)
    articles.sort(key=lambda x: x["weight"], reverse=True)
    return articles[:count]


def slugify(text: str) -> str:
    """Create URL-friendly slug."""
    if re.search(r"[\u3000-\u9fff]", text):
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        if not slug or len(slug) < 3:
            slug = f"summary-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return slug[:80]
    else:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        return slug[:80]


def generate_summary(article: dict, test: bool = False) -> Path | None:
    """Generate a summary article from a source article."""
    title = article["title"]
    url = article["url"]
    lang = article["lang"]
    category = article["category"]

    print(f"  Fetching article: {title[:60]}...")
    article_text = fetch_article_text(url)
    if not article_text or len(article_text) < 100:
        print(f"  Skipping: could not extract enough text from {url}", file=sys.stderr)
        return None

    prompt_template = SUMMARY_PROMPT_JA if lang == "ja" else SUMMARY_PROMPT_EN
    prompt = prompt_template.format(title=title, source_url=url, article_text=article_text)

    print(f"  Summarizing: [{lang}] {title[:60]}...")
    response = call_ollama(prompt)

    try:
        parsed = extract_json(response)
    except ValueError as e:
        print(f"  Failed to parse summary: {e}", file=sys.stderr)
        return None

    summary_title = parsed.get("title", f"Summary: {title[:50]}")
    description = parsed.get("description", "")
    tags = parsed.get("tags", [])
    body = parsed.get("body", "")

    # Ensure source attribution is included
    source_section = f"\n\n## {'出典' if lang == 'ja' else 'Sources'}\n\n- [{title}]({url})\n"
    if url not in body:
        body += source_section

    if test:
        print(f"\n--- Summary Preview ---")
        print(f"Title: {summary_title}")
        print(f"Description: {description}")
        print(f"Tags: {tags}")
        print(f"Body length: {len(body)} chars")
        print(f"Body preview:\n{body[:500]}...")
        return None

    # Create Hugo content file
    date = datetime.now(tz=JST).strftime("%Y-%m-%dT%H:%M:%S+09:00")
    slug = slugify(summary_title)
    cat_names = {
        "ai": {"ja": "AI / Machine Learning", "en": "AI / Machine Learning"},
        "tech": {"ja": "テクノロジー", "en": "Technology"},
        "research": {"ja": "研究", "en": "Research"},
    }
    cat_name = cat_names.get(category, cat_names["tech"])[lang]
    cover_image = f"/images/covers/{category}.svg"

    front_matter = f"""---
title: "{summary_title}"
date: {date}
description: "{description}"
tags: {json.dumps(tags, ensure_ascii=False)}
categories: ["{cat_name}"]
slug: "{slug}"
type: "summary"
cover:
  image: "{cover_image}"
  alt: "{summary_title}"
  relative: false
ShowToc: true
TocOpen: false
draft: false
---

"""

    content = front_matter + body + "\n"

    output_dir = CONTENT_DIR / lang / category
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{slug}.md"
    output_path.write_text(content, encoding="utf-8")
    print(f"  Saved: {output_path.relative_to(BLOG_ROOT)}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate summary articles from trending news")
    parser.add_argument("--count", "-n", type=int, default=1, help="Number of summaries to generate (default: 1)")
    parser.add_argument("--lang", "-l", choices=["ja", "en"], default=None, help="Force language (default: auto)")
    parser.add_argument("--test", action="store_true", help="Test mode: preview without saving")
    parser.add_argument("--model", "-m", default=None, help="Ollama model to use")
    args = parser.parse_args()

    global MODEL
    if args.model:
        MODEL = args.model

    print("Fetching top articles for summarization...", file=sys.stderr)
    articles = get_top_articles(count=args.count, lang=args.lang)

    if not articles:
        print("No articles found for summarization.", file=sys.stderr)
        sys.exit(1)

    generated = []
    failed = []
    for article in articles:
        try:
            path = generate_summary(article, test=args.test)
            if path:
                generated.append(path)
        except Exception as e:
            print(f"  FAILED: {article['title'][:50]} ({e})", file=sys.stderr)
            failed.append(article["title"])

    if not args.test:
        print(f"\nGenerated {len(generated)} summaries, {len(failed)} failed.")


if __name__ == "__main__":
    main()

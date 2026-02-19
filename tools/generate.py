#!/usr/bin/env python3
"""
AI Tech Lab - Article Generator
Generates SEO-optimized blog articles using local Ollama LLM.

Usage:
  python generate.py --keyword "ローカルLLMの始め方" --lang ja --category ai
  python generate.py --keyword "How to fine-tune LLMs" --lang en --category ai
  python generate.py --batch keywords.txt
"""

import argparse
import html
import json
import re
import subprocess
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from pathlib import Path

OLLAMA_URL = "http://127.0.0.1:11434/api/generate"
MODEL = "llama3.3:70b-instruct-q4_K_M"
SEARCH_ENABLED = True
BLOG_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = BLOG_ROOT / "content"

CATEGORIES = {
    "ai": {"ja": "AI / Machine Learning", "en": "AI / Machine Learning"},
    "tech": {"ja": "テクノロジー", "en": "Technology"},
    "research": {"ja": "研究", "en": "Research"},
}

PROMPT_JA = """あなたはSEOに精通したテクニカルライターです。以下のキーワードについて、高品質なブログ記事を書いてください。

キーワード: {keyword}
カテゴリ: {category}
{web_context}
以下のJSON形式で出力してください。他の文言は一切不要です。JSONのみ返してください。
{{
  "title": "SEOに最適化されたタイトル（60文字以内）",
  "description": "メタディスクリプション（120文字以内）",
  "tags": ["タグ1", "タグ2", "タグ3", "タグ4", "タグ5"],
  "body": "記事本文（マークダウン形式、## 見出しを4-6個使い、各セクション200-400字、合計2000-3000字）"
}}

記事の要件:
- 上記のWeb検索結果を参考にして、最新かつ正確な情報を記載する
- 事実に基づいた正確な情報のみ記載する。確信がない情報は書かないこと
- ツールやライブラリの開発元・所属は正確に記載する（例：OllamaはOllama社のOSS、LlamaはMeta開発）
- 読者にとって実用的で具体的な内容にする
- 専門用語には簡潔な説明を加える
- コード例やコマンド例がある場合はコードブロックで記載
- 自然な日本語で書く
- 「まとめ」セクションを最後に含める
- 架空の情報や不確かな統計データを含めないこと
"""

PROMPT_EN = """You are a technical writer with SEO expertise. Write a high-quality blog article about the following keyword.

Keyword: {keyword}
Category: {category}
{web_context}
Output ONLY in the following JSON format. No other text.
{{
  "title": "SEO-optimized title (under 60 characters)",
  "description": "Meta description (under 160 characters)",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5"],
  "body": "Article body in Markdown format, use 4-6 ## headings, 150-300 words per section, 1500-2500 words total"
}}

Article requirements:
- Use the web search results above as reference for current and accurate information
- Only include factually accurate information. Do not fabricate details
- Accurately attribute tools/libraries to their correct creators (e.g., Ollama is by Ollama Inc, Llama by Meta)
- Practical and specific content for readers
- Include brief explanations for technical terms
- Use code blocks for code/command examples where applicable
- Write in natural, engaging English
- Include a "Conclusion" section at the end
- Do not include made-up statistics or unverified claims
"""


def web_search(query: str, num_results: int = 5) -> str:
    """Search DuckDuckGo and return a summary of results."""
    try:
        encoded = urllib.parse.quote(query)
        url = f"https://html.duckduckgo.com/html/?q={encoded}"
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; BlogBot/1.0)"
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")

        # Extract result snippets from DDG HTML
        results = []
        # Find result blocks
        snippets = re.findall(
            r'class="result__snippet"[^>]*>(.*?)</[^>]+>',
            raw, re.DOTALL
        )
        titles = re.findall(
            r'class="result__a"[^>]*>(.*?)</a>',
            raw, re.DOTALL
        )

        for i in range(min(num_results, len(snippets))):
            title = re.sub(r'<[^>]+>', '', titles[i]) if i < len(titles) else ""
            snippet = re.sub(r'<[^>]+>', '', snippets[i])
            title = html.unescape(title).strip()
            snippet = html.unescape(snippet).strip()
            if title or snippet:
                results.append(f"- {title}: {snippet}")

        return "\n".join(results) if results else "No search results found."
    except Exception as e:
        print(f"  Web search failed: {e}", file=sys.stderr)
        return "Web search unavailable."


def call_ollama(prompt: str) -> str:
    data = json.dumps({
        "model": MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 8192, "temperature": 0.7},
    }).encode()

    req = urllib.request.Request(
        OLLAMA_URL,
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read().decode())
            return result.get("response", "")
    except Exception as e:
        raise RuntimeError(f"Ollama API error: {e}")


def extract_json(text: str) -> dict:
    """Extract article fields from LLM response using regex-based extraction.

    More robust than JSON parsing since LLMs often produce invalid JSON
    (unescaped quotes in code blocks, raw newlines, truncated output).
    """
    result = {}

    # Extract title
    m = re.search(r'"title"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if m:
        result["title"] = m.group(1)

    # Extract description
    m = re.search(r'"description"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
    if m:
        result["description"] = m.group(1)

    # Extract tags
    m = re.search(r'"tags"\s*:\s*\[(.*?)\]', text, re.DOTALL)
    if m:
        tags_str = m.group(1)
        result["tags"] = re.findall(r'"((?:[^"\\]|\\.)*)"', tags_str)

    # Extract body - everything after "body": " until the last possible closing
    m = re.search(r'"body"\s*:\s*"', text)
    if m:
        body_start = m.end()
        # Find the body content - take everything from body_start
        # and work backwards from the end to find where the body value ends
        remaining = text[body_start:]

        # Try to find the closing pattern: "\n} or "} at end of response
        # Work backwards to find the last unescaped quote
        body = remaining
        # Remove trailing } and whitespace
        body = body.rstrip()
        if body.endswith("}"):
            body = body[:-1].rstrip()
        if body.endswith("}"):
            body = body[:-1].rstrip()
        # Remove trailing quote if present
        if body.endswith('"'):
            body = body[:-1]

        # Unescape JSON string escapes
        body = body.replace("\\n", "\n").replace("\\t", "\t").replace('\\"', '"').replace("\\\\", "\\")
        result["body"] = body

    if not result.get("title") and not result.get("body"):
        raise ValueError(f"Could not extract article fields from response:\n{text[:500]}")

    return result


def slugify(text: str) -> str:
    """Create URL-friendly slug from text."""
    # For Japanese, use a hash-based approach
    if re.search(r"[\u3000-\u9fff]", text):
        # Transliterate common words, fallback to keyword-based slug
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        if not slug or len(slug) < 3:
            slug = f"article-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        return slug[:80]
    else:
        slug = re.sub(r"[^\w\s-]", "", text.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        return slug[:80]


def generate_article(keyword: str, lang: str, category: str) -> Path:
    """Generate a single article and save it as a Hugo content file."""
    if category not in CATEGORIES:
        print(f"Invalid category: {category}. Use: {', '.join(CATEGORIES.keys())}")
        sys.exit(1)

    if lang not in ("ja", "en"):
        print(f"Invalid language: {lang}. Use: ja, en")
        sys.exit(1)

    cat_name = CATEGORIES[category][lang]
    prompt_template = PROMPT_JA if lang == "ja" else PROMPT_EN

    # Web search for real-time context
    web_context = ""
    if SEARCH_ENABLED:
        print(f"  Searching web: {keyword} ...")
        search_results = web_search(keyword)
        if search_results and "unavailable" not in search_results.lower():
            web_context = f"\n最新のWeb検索結果（参考情報）:\n{search_results}\n" if lang == "ja" \
                else f"\nRecent web search results (reference):\n{search_results}\n"

    prompt = prompt_template.format(keyword=keyword, category=cat_name, web_context=web_context)

    print(f"  Generating: [{lang}] [{category}] {keyword} ...")
    response = call_ollama(prompt)

    try:
        article = extract_json(response)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"  Failed to parse JSON: {e}", file=sys.stderr)
        print(f"  Raw response (first 500 chars):\n{response[:500]}", file=sys.stderr)
        raise

    title = article.get("title", keyword)
    description = article.get("description", "")
    tags = article.get("tags", [])
    body = article.get("body", "")

    # Create front matter
    date = datetime.now().strftime("%Y-%m-%dT%H:%M:%S+09:00")
    slug = slugify(title)

    # Map category to cover image
    cover_image = f"/images/covers/{category}.svg"

    front_matter = f"""---
title: "{title}"
date: {date}
description: "{description}"
tags: {json.dumps(tags, ensure_ascii=False)}
categories: ["{cat_name}"]
slug: "{slug}"
cover:
  image: "{cover_image}"
  alt: "{title}"
  relative: false
ShowToc: true
TocOpen: false
draft: false
---

"""

    content = front_matter + body + "\n"

    # Save file
    filename = f"{slug}.md"
    output_dir = CONTENT_DIR / lang / category
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    output_path.write_text(content, encoding="utf-8")
    print(f"  Saved: {output_path.relative_to(BLOG_ROOT)}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate blog articles using local LLM")
    parser.add_argument("--keyword", "-k", help="Article keyword/topic")
    parser.add_argument("--lang", "-l", default="ja", choices=["ja", "en"], help="Language (default: ja)")
    parser.add_argument("--category", "-c", default="ai", choices=list(CATEGORIES.keys()), help="Category (default: ai)")
    parser.add_argument("--batch", "-b", help="Path to keywords file (one per line, format: keyword|lang|category)")
    parser.add_argument("--model", "-m", default=None, help="Ollama model to use (default: llama3.3:70b-instruct-q4_K_M)")
    parser.add_argument("--no-search", action="store_true", help="Disable web search for context")
    args = parser.parse_args()

    global MODEL, SEARCH_ENABLED
    if args.model:
        MODEL = args.model
    if args.no_search:
        SEARCH_ENABLED = False

    if args.batch:
        batch_file = Path(args.batch)
        if not batch_file.exists():
            print(f"Batch file not found: {batch_file}")
            sys.exit(1)

        generated = []
        failed = []
        for line in batch_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("|")
            keyword = parts[0].strip()
            lang = parts[1].strip() if len(parts) > 1 else "ja"
            category = parts[2].strip() if len(parts) > 2 else "ai"
            try:
                path = generate_article(keyword, lang, category)
                generated.append(path)
            except Exception as e:
                print(f"  SKIPPED: {keyword} ({e})", file=sys.stderr)
                failed.append(keyword)

        print(f"\nGenerated {len(generated)} articles, {len(failed)} failed.")
        if failed:
            print(f"Failed: {', '.join(failed)}")

    elif args.keyword:
        generate_article(args.keyword, args.lang, args.category)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()

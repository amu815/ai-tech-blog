---
title: "PythonでWebスクレイピング入門:初心者向け実践ガイド"
date: 2026-02-20T04:39:03+09:00
description: "Pythonを活用したWebスクレイピングの基礎を学ぶ。requestsやBeautifulSoupの使い方と実用例を解説"
tags: ["Python", "Webスクレイピング", "BeautifulSoup", "requests", "ゼロから始める"]
categories: ["テクノロジー"]
slug: "pythonでwebスクレイピング入門初心者向け実践ガイド"
cover:
  image: "/images/covers/tech.svg"
  alt: "PythonでWebスクレイピング入門:初心者向け実践ガイド"
  relative: false
ShowToc: true
TocOpen: false
draft: false
---

## Webスクレイピングとは？
Webスクレイピングは、ウェブページから必要な情報を自動収集する技術です。Pythonはその豊富なライブラリと簡潔な構文により、スクレイピングに最適な言語です。この記事では、requestsとBeautifulSoupの基本的な使い方を学びながら、実際のコード例を通じて初心者でも理解できるように解説します。

## 必要な環境とライブラリのインストール
Python 3.xをインストール後、以下のコマンドで必須ライブラリをインストールします。

```bash
pip install requests beautifulsoup4
```

`requests`はHTTPリクエストを送信し、HTMLを取得します。`beautifulsoup4`はHTMLを解析して要素を抽出するためのライブラリです。この2つの組み合わせがWebスクレイピングの基本構成です。

## 実践:シンプルなスクレイピングコード
以下は、Pythonでスクレイピングを実行する基本的なコード例です。

```python
import requests
from bs4 import BeautifulSoup

url = 'https://example.com'
response = requests.get(url)
soup = BeautifulSoup(response.text, 'html.parser')

# ページタイトルを取得
print(soup.title.string)

# 全てのリンクを取得
tags = soup.find_all('a')
for tag in tags:
    print(tag.get('href'))
```

このコードでは、指定したURLからHTMLを取得し、BeautifulSoupで解析しています。`find_all`メソッドで複数の要素を取得でき、`get`メソッドで属性値（例: href）を抽出します。

## エラーハンドリングと注意点
スクレイピングでは以下のようなエラーが発生する可能性があります。

```python
try:
    response = requests.get(url, timeout=10)
    response.raise_for_status()  # 404や500系エラー時に例外を発生
except requests.exceptions.RequestException as e:
    print(f'エラーが発生しました: {e}')
```

また、対象サイトのrobots.txtや利用規約を確認し、法律や倫理に配慮することが重要です。頻繁なリクエストはサーバー負荷を高めるため、`time.sleep()`でインターバルを空けましょう。

## JavaScript動的なページへの対応
一部のウェブサイトはJavaScriptで動的にコンテンツを読み込みます。このような場合、SeleniumやPlaywrightなどのツールが必要です。

```python
from selenium import webdriver

driver = webdriver.Chrome()
driver.get('https://example.com')
print(driver.title)
driver.quit()
```

Seleniumはブラウザを自動操作するため、JavaScriptが実行済みのHTMLを取得できますが、処理速度は遅いです。必要に応じて使い分けると良いでしょう。

## まとめ
PythonでのWebスクレイピングは、データ取得の効率化に大きく貢献します。requestsとBeautifulSoupの基本的な使い方を理解し、エラーハンドリングや法律への配慮を怠らないことが成功の鍵です。まずはシンプルな例から試し、複雑なプロジェクトに応じてツールを拡充していきましょう。

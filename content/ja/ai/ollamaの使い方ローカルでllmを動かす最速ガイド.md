---
title: "Ollamaの使い方：ローカルでLLMを動かす最速ガイド"
date: 2026-02-20T05:47:40+09:00
description: "Ollamaを使ってローカルでLLMを動かす手順を解説。インストールからカスタマイズまで、初心者向けの最速ガイド。"
tags: ["Ollama", "LLM", "ローカル実行", "AIチュートリアル", "マシンラーニング"]
categories: ["AI / Machine Learning"]
slug: "ollamaの使い方ローカルでllmを動かす最速ガイド"
ShowToc: true
TocOpen: false
draft: false
---

## Ollamaとは？
Ollamaは、ローカル環境で大規模言語モデル（LLM）を簡単に実行できるオープンソースツールです。Cloudflare開発のこのツールは、モデルのダウンロード・実行・カスタマイズをワンクリックで実現します。LLM（Large Language Model）は自然言語処理の分野で活躍するAIモデルで、ChatGPTやLlamaなどがあります。

## インストール手順
Ollamaを導入するには、以下のコマンドでインストールします。
```bash
# macOS（Homebrew）
brew install ollama

# Windows
ollama install

# Dockerユーザー
docker run -p 11434:11434 -v ollama:/root/.ollama ollama/ollama
```
インストール後、`ollama version`でバージョン確認をしましょう。エラーが出た場合は、公式GitHubリポジトリのIssueセクションを参照。

## モデルのダウンロードと実行
Ollamaでは、以下のようにモデルを動かせます。
```bash
# モデル一覧確認
ollama list

# モデルダウンロード（例：Llama2）
ollama pull llama2

# モデル実行
ollama run llama2
```
実行後、以下のようにプロンプトを入力できます。
```
> こんにちは！
こんにちは！何かお手伝いできますか？
```

## 進階：カスタムモデルの作成
Ollamaはカスタムモデルのトレーニングも可能です。以下の手順で行えます。
1. **データ準備**：JSON形式の対話データを用意
2. **モデル構築**：`ollama create`コマンドでモデル作成
3. **ファインチューニング**：事前学習済みモデルを微調整

```bash
# カスタムモデル作成例
ollama create my-model -f config.yaml

# ファインチューニング
ollama finetune llama2 my-model -d training_data.json
```

## パフォーマンス最適化
ローカル実行のメリットを最大限に活かすために、以下を参考にしてください。
- **GPU利用**：CUDA対応環境で`CUDA_VISIBLE_DEVICES=0 ollama run`と実行
- **メモリ最適化**：`OLLAMA_MAX_LOADED_MODELS=2`でメモリ使用量を制限
- **高速起動**：`ollama serve`で常駐サーバーを起動

## まとめ
OllamaはLLMのローカル実行を簡略化する優れたツールです。インストールからカスタムモデル作成まで、シンプルなコマンドで実現できます。データプライバシーの確保や低遅延な処理が必要な場合に特に有用です。本記事の手順を参考に、ぜひローカルでLLMの力を活用してください。

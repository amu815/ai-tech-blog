---
title: "Docker Composeで開発環境を構築"
date: 2026-02-20T08:26:06+09:00
description: "Docker Composeを使用して開発環境を効率的に構築する方法について解説します。"
tags: ["Docker", "Docker Compose", "開発環境", "テクノロジー", "コンテナ化"]
categories: ["テクノロジー"]
slug: "docker-composeで開発環境を構築"
cover:
  image: "/images/covers/tech.svg"
  alt: "Docker Composeで開発環境を構築"
  relative: false
ShowToc: true
TocOpen: false
draft: false
---


## はじめに
Docker Composeは、複数のコンテナを簡単に管理できるツールです。開発環境の構築に最適な選択肢となります。この記事では、Docker Composeで開発環境を構築する方法について詳しく解説します。

## Docker Composeの概要
Docker Composeは、Docker社が提供しているOSS(オープンソースソフトウェア)です。複数のコンテナ間のネットワーク設定やボリュームマウントなどを簡単に管理できます。

## 開発環境の構築方法
開発環境を構築するには、以下の手順を実行します。
1. **Docker Composeのインストール**: まず、Docker Composeをインストールします。インストール方法は、OSによって異なりますので、公式ドキュメントを参照してください。
2. **docker-compose.ymlファイルの作成**: 次に、プロジェクトディレクトリ内に`docker-compose.yml`ファイルを作成します。このファイルには、コンテナの設定やサービス間の依存関係などが記述されます。

```yml
version: '3'
services:
  web:
    build: .
    ports:
      - "80:80"
    depends_on:
      - db
    environment:
      - DATABASE_HOST=db
      - DATABASE_USER=root
      - DATABASE_PASSWORD=password
  db:
    image: mysql:8.0
    environment:
      - MYSQL_ROOT_PASSWORD=password
      - MYSQL_DATABASE=mydb
```

3. **コンテナの起動**: `docker-compose.yml`ファイルが作成できたら、以下のコマンドを実行してコンテナを起動します。
```bash
docker-compose up -d
```
4. **開発環境へのアクセス**: コンテナが起動したら、開発環境にアクセスできます。例えば、Webサーバーの場合は`http://localhost:80`にアクセスしてください。

## Docker Composeの便利な機能
Docker Composeには、開発者にとって非常に便利な機能があります。
- **依存関係の管理**: `depends_on`ディレクティブを使用すると、サービス間の依存関係を簡単に定義できます。
- **環境変数の設定**: `environment`ディレクティブを使用すると、コンテナ内で使用する環境変数を簡単に設定できます。

## まとめ
この記事では、Docker Composeを使用して開発環境を構築する方法について解説しました。Docker Composeは、複数のコンテナを簡単に管理できるため、開発環境の構築に最適な選択肢となります。また、依存関係の管理や環境変数の設定など、便利な機能が多数用意されています。開発環境の効率化を図る上で、Docker Composeは非常に有用なツールであると言えるでしょう。
"
}
```

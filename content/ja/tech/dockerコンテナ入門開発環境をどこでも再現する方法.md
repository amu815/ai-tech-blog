---
title: "Dockerコンテナ入門：開発環境をどこでも再現する方法"
date: 2026-02-20T04:36:28+09:00
description: "Dockerコンテナで開発環境を再現する方法を解説。初心者向けに実践的な手順とコマンド例を紹介します。"
tags: ["Docker", "開発環境", "コンテナ化", "DevOps", "CI/CD"]
categories: ["テクノロジー"]
slug: "dockerコンテナ入門開発環境をどこでも再現する方法"
cover:
  image: "/images/covers/tech.svg"
  alt: "Dockerコンテナ入門：開発環境をどこでも再現する方法"
  relative: false
ShowToc: true
TocOpen: false
draft: false
---

## Dockerコンテナとは何か
Dockerはアプリケーションを独立した環境（コンテナ）にパッケージ化するテクノロジーです。従来の仮想マシンと異なり、ホストOSのカーネルを共有するため軽量で高速です。開発者はDockerイメージを定義し、それを実行してコンテナを生成します。これにより、環境依存の問題（"私の環境では動く"）を解決できます。

## Dockerを使うメリット
1. **環境一貫性**: ローカル、CIサーバー、本番環境で同じ設定が維持されます。
2. **即時デプロイ**: コンテナをビルドして実行するだけで、複雑な依存関係を管理する必要がありません。
3. **軽量性**: 仮想マシンよりも少ないリソースで複数のコンテナを同時に実行できます。

## Dockerコンテナの基本操作
以下はDockerの基本コマンド例です。
```bash
# イメージをダウンロード
$ docker pull nginx

# コンテナを起動
$ docker run -d -p 80:80 nginx

# 実行中のコンテナを確認
$ docker ps

# コンテナの停止
$ docker stop <container_id>
```
`docker run`コマンドで`-d`はデーモンモード、`-p`はポートマッピングを指定します。この例ではNginxサーバーをローカルで起動しています。

## 開発環境の再現手順
1. **Dockerfile作成**
アプリケーションの依存関係と構成を定義します。
```Dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "app.py"]
```
2. **イメージビルド**
`$ docker build -t myapp .`
3. **コンテナ起動**
`$ docker run -p 5000:5000 myapp`
これにより、誰でも同じ環境でアプリケーションを実行できます。

## トラブルシューティングとベストプラクティス
- **ログ確認**: `$ docker logs <container_id>`
- **データ永続化**: `-v`オプションでホストのディレクトリをマウントします。
- **複数コンテナの管理**: `docker-compose.yml`を使用してサービスを定義します。

## まとめ
Dockerコンテナは開発環境の再現と協業を効率化する強力なツールです。Dockerfileの作成、イメージのビルド、コンテナの起動という3つのステップで、環境依存を最小限に抑えられます。本記事の手順を活用し、プロジェクトの再現性を高めてください。

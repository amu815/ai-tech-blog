---
title: "Linux初心者必見！超基礎コマンド20選と使い方"
date: 2026-02-20T04:48:20+09:00
description: "Linux初心者向けに必須コマンド20個を解説。ファイル操作やシステム確認など、実践で使えるコマンドをわかりやすく紹介します。"
tags: ["Linux", "コマンド", "初心者", "テクノロジー", "システム管理"]
categories: ["テクノロジー"]
slug: "linux初心者必見超基礎コマンド20選と使い方"
ShowToc: true
TocOpen: false
draft: false
---

## Linuxコマンドの基本と重要性
Linuxコマンドは、OSを効率的に操作するための必須ツールです。GUI操作に依存せず、ターミナルから直接ファイルやプロセスを管理できます。特にサーバー運用や開発環境構築ではコマンドが必須です。本記事では、初心者向けのコマンド20個をカテゴリ別に解説します。

## ファイル操作コマンド
ファイル操作はLinuxの基本です。
- `ls`: ファイル一覧表示
  ```bash
  ls -l # 詳細表示
  ls /home/user/Documents # 指定ディレクトリ表示
  ```
- `cd`: ディレクトリ移動
  ```bash
  cd /var/log # /var/logへ移動
  cd .. # 1階層上のディレクトリへ
  ```
- `mkdir`: ディレクトリ作成
  ```bash
  mkdir new_folder # 新規作成
  mkdir -p a/b/c # 親ディレクトリを自動生成
  ```
- `cp`/`mv`: コピー・移動
  ```bash
  cp file.txt backup.txt # コピー
  mv old_name new_name # ファイル名変更
  ```
- `rm`: 削除
  ```bash
  rm file.txt # ファイル削除
  rm -r folder/ # ディレクトリ再帰削除
  ```

## システム情報確認コマンド
システム状況を確認するコマンドです。
- `df`: ディスク使用状況
  ```bash
  df -h # 人間可読な形式で表示
  ```
- `free`: メモリ状況
  ```bash
  free -m # メガバイト単位で表示
  ```
- `top`: 実時間プロセス監視
  ```bash
  top
  # Ctrl+Cで終了
  ```
- `ps`: プロセス一覧
  ```bash
  ps aux # 全プロセス表示
  ```
- `uptime`: システム稼働時間
  ```bash
  uptime
  ```

## ユーザー管理コマンド
複数ユーザー環境での操作に。
- `useradd`: ユーザー追加
  ```bash
  sudo useradd newuser
  sudo passwd newuser # パスワード設定
  ```
- `usermod`: ユーザー変更
  ```bash
  sudo usermod -aG sudo newuser # sudoグループ追加
  ```
- `groupadd`: グループ追加
  ```bash
  sudo groupadd developers
  ```

## プロセス管理コマンド
- `kill`: プロセス終了
  ```bash
  kill 1234 # PID 1234のプロセス終了
  kill -9 1234 # 強制終了
  ```
- `pkill`: 名前でプロセス終了
  ```bash
  pkill firefox
  ```

## ネットワークコマンド
- `ping`: 接続確認
  ```bash
  ping google.com
  # Ctrl+Cで終了
  ```
- `ifconfig`: ネットワーク設定
  ```bash
  ifconfig eth0 # eth0の設定確認
  ```
- `netstat`: ネットワーク接続一覧
  ```bash
  netstat -tuln # TCP/UDP接続表示
  ```
- `curl`/`wget`: ファイル取得
  ```bash
  curl https://example.com
  wget https://example.com/file.txt
  ```

## まとめ
本記事で紹介した20個のコマンドをマスターすれば、Linuxの基本操作はカバーできます。特に`ls`/`cd`/`cp`/`rm`は頻繁に使用します。コマンドは練習で覚えられるため、実際にターミナルで試してみてください。

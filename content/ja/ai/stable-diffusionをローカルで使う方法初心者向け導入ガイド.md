---
title: "Stable Diffusionをローカルで使う方法｜初心者向け導入ガイド"
date: 2026-02-20T04:28:42+09:00
description: "画像生成AI Stable Diffusionのローカル環境構築手順。PythonやGPU設定を含む実践的な導入ガイドを解説"
tags: ["Stable Diffusion", "画像生成AI", "ローカル導入", "Python", "GPU利用"]
categories: ["AI / Machine Learning"]
slug: "stable-diffusionをローカルで使う方法初心者向け導入ガイド"
ShowToc: true
TocOpen: false
draft: false
---

## Stable Diffusionとは？
Stable Diffusionは拡散モデルを用いた画像生成AIで、テキストから高品質な画像を生成します。ローカル環境での運用により、プライバシー保護やコスト削減が可能です。本記事ではWindows/Mac環境での導入手順を解説します。

## 導入に必要な環境
以下を確認してください：
- Python 3.10以上（パッケージ管理に必要）
- CUDA対応GPU（NVIDIA製推奨）
- 16GB RAM以上
- 50GB以上の空き容量

### インストール手順
1. **Pythonのインストール**
   ```bash
   # Homebrewでインストール（Mac）
   brew install python@3.10

   # Windowsの場合、公式サイトからインストーラーをダウンロード
   https://www.python.org/downloads/
   ```

2. **仮想環境の作成**
   ```bash
   python -m venv sd_env
   source sd_env/bin/activate  # Windowsはsd_env\Scripts\activate
   ```

3. **依存関係のインストール**
   ```bash
   pip install -r requirements.txt
   ```

4. **モデルファイルのダウンロード**
   ```bash
   # HuggingFaceからモデルIDを取得
   curl -L -X GET https://huggingface.co/stabilityai/stable-diffusion-2-1-base/resolve/main/model_index.json
   ```

5. **WebUIの起動**
   ```bash
   python webui.py --listen
   ```

## よくあるエラーと対処法
### GPUが認識されない場合
- `nvidia-smi`コマンドでドライバが正しくインストールされているか確認
- CUDA Toolkitのバージョン確認（ドライバとCUDAバージョンの整合性）

### メモリ不足エラー
- `--precision full`を指定してFP32で実行
- CPU利用：`--no-half`オプションを追加

## 高度な設定
### モデルカスタマイズ
`config.yaml`ファイルで以下の設定が可能です：
```yaml
unet:
  pretrained_model_name_or_path: ./models/unet
  in_channels: 4
```

### カスタムスクリプトの導入
`scripts/`ディレクトリに`.py`ファイルを配置することで、独自の拡張機能を追加可能です。

## まとめ
Stable Diffusionのローカル導入により、画像生成のプロセスを完全にコントロールできます。初期設定にはPythonやGPUの知識が必要ですが、手順を丁寧に実行すれば初心者でも導入可能です。今後のカスタマイズや性能向上のため、仮想環境の活用とモデルファイルの理解を深めることをおすすめします。

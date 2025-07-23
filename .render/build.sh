#!/usr/bin/env bash

echo "Using Python version:"
python --version  # デバッグ用出力

# Python 3.12 が使えるなら pyenv 経由で切り替え
# もしダメなら Docker コンテナのベースを変えるしかない

pip install --upgrade pip
pip install -r requirements.txt
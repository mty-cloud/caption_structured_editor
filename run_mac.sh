#!/bin/bash
# macOS 启动脚本
# 使用方式：双击此文件，或在终端执行 bash run_mac.sh

cd "$(dirname "$0")"
echo "启动 机标结构化修改器..."
python3 main.py

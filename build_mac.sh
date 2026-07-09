#!/bin/bash
# macOS 打包脚本
# 在 macOS 上运行，将 Python 项目打包为独立的 .app

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================"
echo "  机标结构化修改器 - macOS 打包"
echo "============================================"

# 检查 PyInstaller
if ! command -v pyinstaller &> /dev/null; then
    echo "→ 正在安装 PyInstaller..."
    pip3 install pyinstaller
fi

echo "→ 清理旧构建..."
rm -rf build dist

echo "→ 执行 PyInstaller 打包..."
pyinstaller build.spec

echo ""
echo "============================================"
echo "  ✅ 打包完成！"
echo "============================================"

APP_PATH="$SCRIPT_DIR/dist/机标结构化修改器.app"
if [ -d "$APP_PATH" ]; then
    echo ""
    echo "  应用路径：$APP_PATH"
    echo "  大小：$(du -sh "$APP_PATH" | cut -f1)"
    echo ""
    echo "  使用方法："
    echo "  1. 打开 Finder → 前往 dist/ 目录"
    echo "  2. 双击 机标结构化修改器.app"
    echo "  3. 如果提示"无法验证开发者"，请在"
    echo "     系统设置 → 隐私与安全性中点击"仍要打开""
    echo ""
    echo "  分发前可压缩为 ZIP："
    echo "    zip -r 机标结构化修改器-Mac.zip dist/机标结构化修改器.app"
fi

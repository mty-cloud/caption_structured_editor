@echo off
REM Windows 打包脚本
REM 在 Windows 上运行，将 Python 项目打包为独立 .exe

echo ============================================
echo   机标结构化修改器 - Windows 打包
echo ============================================

cd /d "%~dp0"

REM 检查 PyInstaller
pip show pyinstaller >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo → 正在安装 PyInstaller...
    pip install pyinstaller
)

echo → 清理旧构建...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo → 执行 PyInstaller 打包...
pyinstaller build.spec

echo.
echo ============================================
echo   ✅ 打包完成！
echo ============================================

echo.
echo   可执行文件：dist\机标结构化修改器.exe
echo.
echo   使用方法：
echo   1. 将 dist\机标结构化修改器.exe 发送给用户
echo   2. 双击即可运行（无需安装 Python）
echo.
echo   分发前可压缩为 ZIP：
echo     powershell Compress-Archive -Path dist\机标结构化修改器.exe -DestinationPath 机标结构化修改器-Windows.zip
echo.

pause

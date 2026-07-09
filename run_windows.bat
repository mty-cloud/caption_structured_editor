@echo off
REM Windows 启动脚本
REM 双击此文件运行

cd /d "%~dp0"
echo 启动 机标结构化修改器...
python main.py
pause

@echo off
setlocal EnableDelayedExpansion

:: 获取当前脚本所在的目录
set "script_dir=%~dp0"
set "exe_path=%script_dir%build\main\main.exe"

:: 检查exe文件是否存在
if not exist "!exe_path!" (
    echo 错误：找不到可执行文件 !exe_path!
    echo 请确保已构建Markdown Reader应用程序
    pause
    exit /b 1
)

:: 注册为md文件的默认打开程序
echo 正在将Markdown Reader设置为.md文件的默认打开程序...
assoc .md=MarkdownFile
ftype MarkdownFile="!exe_path!" "%%1"

:: 检查是否成功
if errorlevel 1 (
    echo 设置默认程序失败。请以管理员权限运行此脚本。
) else (
    echo 已成功将Markdown Reader设置为.md文件的默认打开程序。
    echo 现在双击.md文件将使用Markdown Reader打开。
)

pause

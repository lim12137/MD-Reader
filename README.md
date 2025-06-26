# Markdown Reader

一个轻量级的Markdown文件阅读器，支持在Windows系统下双击或右键打开Markdown文件，显示图片链接，并能将文件转换为PDF、DOCX和HTML格式保存。

## 功能特性
- 支持双击或右键菜单打开Markdown文件（需完成文件关联注册）
- 显示Markdown内容，包括表格和代码块
- 直接嵌入图片链接
- 将Markdown文件转换为PDF、DOCX和HTML格式
- 支持英语和中文界面切换
- 现代化、扁平化风格的用户界面

## 安装依赖
在运行应用程序之前，请确保安装了以下依赖项：

```bash
pip install -r requirements.txt
```

此外，格式转换功能依赖于`pandoc`。请从[官方网站](https://pandoc.org/installing.html)下载并安装`pandoc`，并确保其路径已添加到系统环境变量中。如果要生成PDF文件，还需要安装LaTeX引擎（如XeLaTeX）。

## 使用方法
1. 运行`main.py`文件启动应用程序：
   ```bash
   python main.py
   ```
2. 通过“文件”菜单打开Markdown文件，或直接双击文件（需完成文件关联）。
3. 使用“转换”菜单选择输出格式（PDF、DOCX、HTML）并保存文件。
4. 使用“语言”菜单切换界面语言（英语或中文）。

## 文件关联
目前文件关联功能尚未实现。后续版本将提供`register.py`脚本，用于在Windows系统中注册Markdown文件关联，以便双击或右键打开文件。

## 打包为EXE
后续版本将提供使用`PyInstaller`打包应用程序为独立EXE文件的指南，以便无需Python环境即可运行。

## 许可证
MIT

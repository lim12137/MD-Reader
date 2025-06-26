import sys
import os
import subprocess
import json
import ctypes
import markdown2
from PySide6.QtWidgets import (QApplication, QMainWindow, QFileDialog, QVBoxLayout, QWidget,
                             QStatusBar, QMessageBox, QLineEdit, QPushButton, QListWidget,
                             QHBoxLayout, QInputDialog, QToolBar, QSizePolicy, QMenu, QDialog)
from PySide6.QtGui import QAction
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebEngineCore import QWebEnginePage
from PySide6.QtCore import QLocale, QTranslator, QUrl, QThread, Signal

class FileLoaderThread(QThread):
    contentLoaded = Signal(str)
    progress = Signal(str)

    def __init__(self, file_path):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.progress.emit('正在读取文件...')
            with open(self.file_path, 'r', encoding='utf-8') as file:
                content = file.read()
            self.progress.emit('正在转换Markdown为HTML...')
            html_content = markdown2.markdown(content, extras=['tables', 'fenced-code-blocks', 'latex', 'mermaid'])
            mathjax_html = """
            <script src="https://cdnjs.cloudflare.com/ajax/libs/mathjax/2.7.7/MathJax.js?config=TeX-AMS-MML_HTMLorMML"></script>
            <script type="text/x-mathjax-config">
                MathJax.Hub.Config({
                    tex2jax: {
                        inlineMath: [['
,'
'], ['\\(','\\)']],
                        displayMath: [['
            self.contentLoaded.emit(html_content)
        except Exception as e:
            self.contentLoaded.emit(f"<html><body><h1>加载文件出错: {str(e)}</h1></body></html>")

class ConvertThread(QThread):
    conversionFinished = Signal(str)
    conversionError = Signal(str)

    def __init__(self, input_file, output_file, format_type, resource_dir):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.format_type = format_type
        self.resource_dir = resource_dir

    def run(self):
        try:
            if getattr(sys, 'frozen', False):
                # If the application is run as a bundle, the PyInstaller bootloader
                # extends the sys module by a flag frozen=True and sets the absolute
                # path of the bundle by the _MEIPASS attribute.
                pandoc_base_path = sys._MEIPASS
            else:
                pandoc_base_path = os.getcwd()
            command = [os.path.join(pandoc_base_path, 'pandoc-3.7.0.2', 'pandoc.exe'), self.input_file, '-o', self.output_file, '--embed-resources', '--standalone', f'--resource-path={self.resource_dir}']
            result = subprocess.run(command,
                                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                                    stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    encoding='utf-8',
                                    errors='ignore')
            if result.returncode == 0:
                self.conversionFinished.emit(f'转换完成: {os.path.basename(self.input_file)} -> {os.path.basename(self.output_file)}')
            else:
                self.conversionError.emit(f'转换失败: Pandoc exited with code {result.returncode}\n{result.stderr}')
        except FileNotFoundError:
            self.conversionError.emit('Pandoc未安装')
        except Exception as e:
            self.conversionError.emit(f'转换过程中发生错误: {str(e)}')

class MarkdownReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.translator = QTranslator()
        self.tags = self.load_tags()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Markdown Reader')
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)
        self.setup_toolbar()
        self.setup_main_layout()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage('就绪')

    def setup_toolbar(self):
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        fileButton = QPushButton('文件')
        fileButton.clicked.connect(self.showFileMenu)
        self.toolbar.addWidget(fileButton)

        tagButton = QPushButton('标签')
        tagButton.clicked.connect(self.showTagMenu)
        self.toolbar.addWidget(tagButton)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        self.searchInput = QLineEdit()
        self.searchInput.setPlaceholderText('搜索...')
        self.searchInput.returnPressed.connect(self.searchText)
        self.toolbar.addWidget(self.searchInput)

        searchButton = QPushButton('搜索')
        searchButton.clicked.connect(self.searchText)
        self.toolbar.addWidget(searchButton)

    def setup_main_layout(self):
        layout = QVBoxLayout()
        self.webView = QWebEngineView()
        layout.addWidget(self.webView, 1)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def openFile(self, fname=None):
        if not fname:
            fname, _ = QFileDialog.getOpenFileName(self, '打开Markdown文件', '', 'Markdown文件 (*.md)')
        if fname:
            self.current_file = fname
            self.statusBar().showMessage(f'正在打开: {os.path.basename(fname)}...')
            self.setEnabled(False)
            self.loader_thread = FileLoaderThread(fname)
            self.loader_thread.contentLoaded.connect(lambda html: self.webView.setHtml(html, QUrl.fromLocalFile(fname)))
            self.loader_thread.progress.connect(self.statusBar().showMessage)
            self.loader_thread.finished.connect(lambda: [self.statusBar().showMessage(f'已打开: {os.path.basename(fname)}'), self.setEnabled(True)])
            self.loader_thread.start()

    def showFileMenu(self):
        menu = QMenu(self)
        openAction = QAction('打开', self)
        openAction.triggered.connect(self.openFile)
        menu.addAction(openAction)

        saveDocxAction = QAction('保存为DOCX', self)
        saveDocxAction.triggered.connect(lambda: self.convertTo('docx'))
        menu.addAction(saveDocxAction)

        saveHtmlAction = QAction('保存为HTML', self)
        saveHtmlAction.triggered.connect(lambda: self.convertTo('html'))
        menu.addAction(saveHtmlAction)

        menu.addSeparator()

        setDefaultAction = QAction('设置为默认Markdown阅读器', self)
        setDefaultAction.triggered.connect(self.setDefaultMdHandler)
        menu.addAction(setDefaultAction)

        menu.exec(self.mapToGlobal(self.toolbar.geometry().bottomLeft()))

    def searchText(self):
        search_term = self.searchInput.text()
        if search_term:
            self.webView.findText(search_term)

    def showTagMenu(self):
        menu = QMenu(self)
        addTagAction = QAction('添加标签', self)
        addTagAction.triggered.connect(self.addTag)
        menu.addAction(addTagAction)

        viewTagsAction = QAction('查看标签', self)
        viewTagsAction.triggered.connect(self.viewTags)
        menu.addAction(viewTagsAction)

        deleteTagAction = QAction('删除标签', self)
        deleteTagAction.triggered.connect(self.deleteTag)
        menu.addAction(deleteTagAction)

        menu.exec(self.mapToGlobal(self.toolbar.geometry().bottomLeft()))

    def searchPrevious(self):
        search_term = self.searchInput.text()
        if not search_term:
            QMessageBox.warning(self, '搜索', '请输入搜索词', QMessageBox.Ok)
            return

        if not hasattr(self, 'last_search_term') or self.last_search_term != search_term:
            self.searchText()

        flags = QWebEnginePage.FindFlag.FindBackward
        self.webView.findText(search_term, flags, lambda found: self.statusBar().showMessage('找到上一个匹配项' if found else '未找到上一个匹配项'))
        self.last_search_term = search_term

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            pos = event.position().toPoint()
            web_view_rect = self.webView.geometry()
            if web_view_rect.contains(pos):
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.md'):
                self.openFile(file_path)
                break

    def addTag(self):
        tag, ok = QInputDialog.getText(self, '添加标签', '输入标签名称:')
        if ok and tag:
            if self.current_file:
                if self.current_file not in self.tags:
                    self.tags[self.current_file] = []
                self.webView.page().runJavaScript("window.scrollY", 0, lambda result: self.storeTagWithPosition(tag, result))
            else:
                self.statusBar().showMessage('请先打开一个文件')

    def viewTags(self):
        if not self.tags:
            QMessageBox.information(self, '标签', '没有标签', QMessageBox.Ok)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('标签列表')
        layout = QVBoxLayout()

        listWidget = QListWidget()
        for file, tags in self.tags.items():
            for tag_info in tags:
                if isinstance(tag_info, dict):
                    tag_name = tag_info.get('name', '未知标签')
                    position = tag_info.get('position', '未知位置')
                    listWidget.addItem(f"{os.path.basename(file)}: {tag_name} (位置: {position})")
                else:
                    listWidget.addItem(f"{os.path.basename(file)}: {tag_info}")
        layout.addWidget(listWidget)

        listWidget.itemDoubleClicked.connect(lambda item: self.jumpToTagPosition(item, dialog))

        closeButton = QPushButton('关闭')
        closeButton.clicked.connect(dialog.close)
        layout.addWidget(closeButton)

        jumpButton = QPushButton('跳转到标签位置')
        jumpButton.clicked.connect(lambda: self.jumpToTagPosition(listWidget.currentItem(), dialog))
        layout.addWidget(jumpButton)

        dialog.setLayout(layout)
        dialog.exec()

    def storeTagWithPosition(self, tag, scrollY):
        tag_info = {'name': tag, 'position': scrollY}
        if tag_info not in self.tags[self.current_file]:
            self.tags[self.current_file].append(tag_info)
            self.save_tags()
            self.statusBar().showMessage(f'已添加标签 "{tag}" 到当前文件，位置: {scrollY}')
        else:
            self.statusBar().showMessage(f'标签 "{tag}" 已存在于当前文件')

    def jumpToTagPosition(self, item, dialog):
        if item:
            text = item.text()
            start_idx = text.find('(位置: ')
            if start_idx != -1:
                position_str = text[start_idx + 7:].rstrip(')')
                try:
                    position = int(position_str)
                    self.webView.page().runJavaScript(f"window.scrollTo(0, {position});", 0, lambda _: None)
                    dialog.close()
                    self.statusBar().showMessage(f'已跳转到标签位置: {position}')
                except ValueError:
                    self.statusBar().showMessage('无法解析标签位置')
            else:
                self.statusBar().showMessage('无法找到标签位置信息')
        else:
            self.statusBar().showMessage('请选择一个标签')

    def convertTo(self, format):
        if not self.current_file:
            return

        base_name = os.path.basename(self.current_file)
        base_name_without_ext = os.path.splitext(base_name)[0]
        default_save_name = f"{base_name_without_ext}.{format}"

        output_file, _ = QFileDialog.getSaveFileName(self, f'保存为{format.upper()}', default_save_name, f'{format.upper()}文件 (*.{format})')
        if output_file:
            self.statusBar().showMessage(f'转换中: {base_name} -> {format.upper()}')
            self.setEnabled(False)
            resource_dir = os.path.dirname(self.current_file)
            self.convert_thread = ConvertThread(self.current_file, output_file, format, resource_dir)
            self.convert_thread.conversionFinished.connect(lambda msg: [self.statusBar().showMessage(msg), self.setEnabled(True)])
            self.convert_thread.conversionError.connect(lambda err: [self.showConversionError(err, format), self.setEnabled(True)])
            self.convert_thread.start()

    def deleteTag(self):
        if not self.tags or not self.current_file or self.current_file not in self.tags:
            QMessageBox.information(self, '删除标签', '当前文件没有标签', QMessageBox.Ok)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('删除标签')
        layout = QVBoxLayout()

        listWidget = QListWidget()
        for tag_info in self.tags[self.current_file]:
            if isinstance(tag_info, dict):
                tag_name = tag_info.get('name', '未知标签')
                position = tag_info.get('position', '未知位置')
                listWidget.addItem(f"{tag_name} (位置: {position})")
            else:
                listWidget.addItem(tag_info)
        layout.addWidget(listWidget)

        deleteButton = QPushButton('删除')
        deleteButton.clicked.connect(lambda: self.removeTag(listWidget.currentItem(), dialog))
        layout.addWidget(deleteButton)

        closeButton = QPushButton('关闭')
        closeButton.clicked.connect(dialog.close)
        layout.addWidget(closeButton)

        dialog.setLayout(layout)
        dialog.exec()

    def removeTag(self, item, dialog):
        if item:
            text = item.text()
            start_idx = text.find('(位置: ')
            tag_name = text.split(' (位置: ')[0] if start_idx != -1 else text
            for tag_info in self.tags[self.current_file][:]:
                if isinstance(tag_info, dict) and tag_info.get('name') == tag_name:
                    self.tags[self.current_file].remove(tag_info)
                    self.save_tags()
                    self.statusBar().showMessage(f'已删除标签 "{tag_name}"')
                    dialog.close()
                    break
                elif tag_info == tag_name:
                    self.tags[self.current_file].remove(tag_info)
                    self.save_tags()
                    self.statusBar().showMessage(f'已删除标签 "{tag_name}"')
                    dialog.close()
                    break
            if not self.tags[self.current_file]:
                del self.tags[self.current_file]
                self.save_tags()
        else:
            self.statusBar().showMessage('请选择一个要删除的标签')

    def showConversionError(self, error_message, format):
        if 'Pandoc未安装' in error_message:
            QMessageBox.critical(self, 'Pandoc未安装', 'Pandoc未安装，转换功能不可用。请安装Pandoc以启用转换功能.<br><br><font color="red">下载链接: <a href="https://pandoc.org/installing.html">https://pandoc.org/installing.html</a></font>', QMessageBox.Ok)
            self.statusBar().showMessage('转换失败: Pandoc未安装')
        else:
            QMessageBox.warning(self, '转换错误', error_message, QMessageBox.Ok)
            self.statusBar().showMessage('转换失败: 发生错误')

    def load_tags(self):
        try:
            with open('tags.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_tags(self):
        with open('tags.json', 'w') as f:
            json.dump(self.tags, f, indent=4)

    def setDefaultMdHandler(self):
        try:
            import winreg
            app_path = os.path.abspath(sys.argv[0])
            if app_path.endswith('.py'):
                QMessageBox.warning(self, '设置默认程序', '无法在开发模式下设置默认程序。请运行编译后的EXE文件。', QMessageBox.Ok)
                return

            # Define the application name and description
            app_name = 'MarkdownReader'
            app_description = 'Markdown Reader Application'

            # Set up the file association for .md files
            # 1. Create or open the .md key
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\.md')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'{app_name}.md')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置.md文件关联: {e}', QMessageBox.Ok)
                return

            # 2. Create or open the application key
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, app_description)
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法创建应用程序键: {e}', QMessageBox.Ok)
                return

            # 3. Set the default icon
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md\DefaultIcon')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{app_path}",0')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置默认图标: {e}', QMessageBox.Ok)
                return

            # 4. Set the shell open command
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md\shell\open\command')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{app_path}" "%1"')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置打开命令: {e}', QMessageBox.Ok)
                return

            # Notify Windows about the change
            # SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL)
            # This requires ctypes.windll.shell32.SHChangeNotify
            # For simplicity, we'll skip this for now, as it often works without it.
            # If issues arise, this can be added.

            QMessageBox.information(self, '设置默认程序', 'Markdown Reader 已成功设置为 .md 文件的默认打开程序。', QMessageBox.Ok)

        except ImportError:
            QMessageBox.critical(self, '错误', '无法导入 winreg 模块。此功能仅在 Windows 上可用。', QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'设置默认程序时发生未知错误: {e}', QMessageBox.Ok)

if __name__ == '__main__':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    app = QApplication(sys.argv)
    ex = MarkdownReader()
    ex.show()
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path) and file_path.endswith('.md'):
            ex.openFile(file_path)
    sys.exit(app.exec())
,'
            self.contentLoaded.emit(html_content)
        except Exception as e:
            self.contentLoaded.emit(f"<html><body><h1>加载文件出错: {str(e)}</h1></body></html>")

class ConvertThread(QThread):
    conversionFinished = Signal(str)
    conversionError = Signal(str)

    def __init__(self, input_file, output_file, format_type, resource_dir):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.format_type = format_type
        self.resource_dir = resource_dir

    def run(self):
        try:
            if getattr(sys, 'frozen', False):
                # If the application is run as a bundle, the PyInstaller bootloader
                # extends the sys module by a flag frozen=True and sets the absolute
                # path of the bundle by the _MEIPASS attribute.
                pandoc_base_path = sys._MEIPASS
            else:
                pandoc_base_path = os.getcwd()
            command = [os.path.join(pandoc_base_path, 'pandoc-3.7.0.2', 'pandoc.exe'), self.input_file, '-o', self.output_file, '--embed-resources', '--standalone', f'--resource-path={self.resource_dir}']
            result = subprocess.run(command,
                                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                                    stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    encoding='utf-8',
                                    errors='ignore')
            if result.returncode == 0:
                self.conversionFinished.emit(f'转换完成: {os.path.basename(self.input_file)} -> {os.path.basename(self.output_file)}')
            else:
                self.conversionError.emit(f'转换失败: Pandoc exited with code {result.returncode}\n{result.stderr}')
        except FileNotFoundError:
            self.conversionError.emit('Pandoc未安装')
        except Exception as e:
            self.conversionError.emit(f'转换过程中发生错误: {str(e)}')

class MarkdownReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.translator = QTranslator()
        self.tags = self.load_tags()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Markdown Reader')
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)
        self.setup_toolbar()
        self.setup_main_layout()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage('就绪')

    def setup_toolbar(self):
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        fileButton = QPushButton('文件')
        fileButton.clicked.connect(self.showFileMenu)
        self.toolbar.addWidget(fileButton)

        tagButton = QPushButton('标签')
        tagButton.clicked.connect(self.showTagMenu)
        self.toolbar.addWidget(tagButton)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        self.searchInput = QLineEdit()
        self.searchInput.setPlaceholderText('搜索...')
        self.searchInput.returnPressed.connect(self.searchText)
        self.toolbar.addWidget(self.searchInput)

        searchButton = QPushButton('搜索')
        searchButton.clicked.connect(self.searchText)
        self.toolbar.addWidget(searchButton)

    def setup_main_layout(self):
        layout = QVBoxLayout()
        self.webView = QWebEngineView()
        layout.addWidget(self.webView, 1)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def openFile(self, fname=None):
        if not fname:
            fname, _ = QFileDialog.getOpenFileName(self, '打开Markdown文件', '', 'Markdown文件 (*.md)')
        if fname:
            self.current_file = fname
            self.statusBar().showMessage(f'正在打开: {os.path.basename(fname)}...')
            self.setEnabled(False)
            self.loader_thread = FileLoaderThread(fname)
            self.loader_thread.contentLoaded.connect(lambda html: self.webView.setHtml(html, QUrl.fromLocalFile(fname)))
            self.loader_thread.progress.connect(self.statusBar().showMessage)
            self.loader_thread.finished.connect(lambda: [self.statusBar().showMessage(f'已打开: {os.path.basename(fname)}'), self.setEnabled(True)])
            self.loader_thread.start()

    def showFileMenu(self):
        menu = QMenu(self)
        openAction = QAction('打开', self)
        openAction.triggered.connect(self.openFile)
        menu.addAction(openAction)

        saveDocxAction = QAction('保存为DOCX', self)
        saveDocxAction.triggered.connect(lambda: self.convertTo('docx'))
        menu.addAction(saveDocxAction)

        saveHtmlAction = QAction('保存为HTML', self)
        saveHtmlAction.triggered.connect(lambda: self.convertTo('html'))
        menu.addAction(saveHtmlAction)

        menu.addSeparator()

        setDefaultAction = QAction('设置为默认Markdown阅读器', self)
        setDefaultAction.triggered.connect(self.setDefaultMdHandler)
        menu.addAction(setDefaultAction)

        menu.exec(self.mapToGlobal(self.toolbar.geometry().bottomLeft()))

    def searchText(self):
        search_term = self.searchInput.text()
        if search_term:
            self.webView.findText(search_term)

    def showTagMenu(self):
        menu = QMenu(self)
        addTagAction = QAction('添加标签', self)
        addTagAction.triggered.connect(self.addTag)
        menu.addAction(addTagAction)

        viewTagsAction = QAction('查看标签', self)
        viewTagsAction.triggered.connect(self.viewTags)
        menu.addAction(viewTagsAction)

        deleteTagAction = QAction('删除标签', self)
        deleteTagAction.triggered.connect(self.deleteTag)
        menu.addAction(deleteTagAction)

        menu.exec(self.mapToGlobal(self.toolbar.geometry().bottomLeft()))

    def searchPrevious(self):
        search_term = self.searchInput.text()
        if not search_term:
            QMessageBox.warning(self, '搜索', '请输入搜索词', QMessageBox.Ok)
            return

        if not hasattr(self, 'last_search_term') or self.last_search_term != search_term:
            self.searchText()

        flags = QWebEnginePage.FindFlag.FindBackward
        self.webView.findText(search_term, flags, lambda found: self.statusBar().showMessage('找到上一个匹配项' if found else '未找到上一个匹配项'))
        self.last_search_term = search_term

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            pos = event.position().toPoint()
            web_view_rect = self.webView.geometry()
            if web_view_rect.contains(pos):
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.md'):
                self.openFile(file_path)
                break

    def addTag(self):
        tag, ok = QInputDialog.getText(self, '添加标签', '输入标签名称:')
        if ok and tag:
            if self.current_file:
                if self.current_file not in self.tags:
                    self.tags[self.current_file] = []
                self.webView.page().runJavaScript("window.scrollY", 0, lambda result: self.storeTagWithPosition(tag, result))
            else:
                self.statusBar().showMessage('请先打开一个文件')

    def viewTags(self):
        if not self.tags:
            QMessageBox.information(self, '标签', '没有标签', QMessageBox.Ok)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('标签列表')
        layout = QVBoxLayout()

        listWidget = QListWidget()
        for file, tags in self.tags.items():
            for tag_info in tags:
                if isinstance(tag_info, dict):
                    tag_name = tag_info.get('name', '未知标签')
                    position = tag_info.get('position', '未知位置')
                    listWidget.addItem(f"{os.path.basename(file)}: {tag_name} (位置: {position})")
                else:
                    listWidget.addItem(f"{os.path.basename(file)}: {tag_info}")
        layout.addWidget(listWidget)

        listWidget.itemDoubleClicked.connect(lambda item: self.jumpToTagPosition(item, dialog))

        closeButton = QPushButton('关闭')
        closeButton.clicked.connect(dialog.close)
        layout.addWidget(closeButton)

        jumpButton = QPushButton('跳转到标签位置')
        jumpButton.clicked.connect(lambda: self.jumpToTagPosition(listWidget.currentItem(), dialog))
        layout.addWidget(jumpButton)

        dialog.setLayout(layout)
        dialog.exec()

    def storeTagWithPosition(self, tag, scrollY):
        tag_info = {'name': tag, 'position': scrollY}
        if tag_info not in self.tags[self.current_file]:
            self.tags[self.current_file].append(tag_info)
            self.save_tags()
            self.statusBar().showMessage(f'已添加标签 "{tag}" 到当前文件，位置: {scrollY}')
        else:
            self.statusBar().showMessage(f'标签 "{tag}" 已存在于当前文件')

    def jumpToTagPosition(self, item, dialog):
        if item:
            text = item.text()
            start_idx = text.find('(位置: ')
            if start_idx != -1:
                position_str = text[start_idx + 7:].rstrip(')')
                try:
                    position = int(position_str)
                    self.webView.page().runJavaScript(f"window.scrollTo(0, {position});", 0, lambda _: None)
                    dialog.close()
                    self.statusBar().showMessage(f'已跳转到标签位置: {position}')
                except ValueError:
                    self.statusBar().showMessage('无法解析标签位置')
            else:
                self.statusBar().showMessage('无法找到标签位置信息')
        else:
            self.statusBar().showMessage('请选择一个标签')

    def convertTo(self, format):
        if not self.current_file:
            return

        base_name = os.path.basename(self.current_file)
        base_name_without_ext = os.path.splitext(base_name)[0]
        default_save_name = f"{base_name_without_ext}.{format}"

        output_file, _ = QFileDialog.getSaveFileName(self, f'保存为{format.upper()}', default_save_name, f'{format.upper()}文件 (*.{format})')
        if output_file:
            self.statusBar().showMessage(f'转换中: {base_name} -> {format.upper()}')
            self.setEnabled(False)
            resource_dir = os.path.dirname(self.current_file)
            self.convert_thread = ConvertThread(self.current_file, output_file, format, resource_dir)
            self.convert_thread.conversionFinished.connect(lambda msg: [self.statusBar().showMessage(msg), self.setEnabled(True)])
            self.convert_thread.conversionError.connect(lambda err: [self.showConversionError(err, format), self.setEnabled(True)])
            self.convert_thread.start()

    def deleteTag(self):
        if not self.tags or not self.current_file or self.current_file not in self.tags:
            QMessageBox.information(self, '删除标签', '当前文件没有标签', QMessageBox.Ok)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('删除标签')
        layout = QVBoxLayout()

        listWidget = QListWidget()
        for tag_info in self.tags[self.current_file]:
            if isinstance(tag_info, dict):
                tag_name = tag_info.get('name', '未知标签')
                position = tag_info.get('position', '未知位置')
                listWidget.addItem(f"{tag_name} (位置: {position})")
            else:
                listWidget.addItem(tag_info)
        layout.addWidget(listWidget)

        deleteButton = QPushButton('删除')
        deleteButton.clicked.connect(lambda: self.removeTag(listWidget.currentItem(), dialog))
        layout.addWidget(deleteButton)

        closeButton = QPushButton('关闭')
        closeButton.clicked.connect(dialog.close)
        layout.addWidget(closeButton)

        dialog.setLayout(layout)
        dialog.exec()

    def removeTag(self, item, dialog):
        if item:
            text = item.text()
            start_idx = text.find('(位置: ')
            tag_name = text.split(' (位置: ')[0] if start_idx != -1 else text
            for tag_info in self.tags[self.current_file][:]:
                if isinstance(tag_info, dict) and tag_info.get('name') == tag_name:
                    self.tags[self.current_file].remove(tag_info)
                    self.save_tags()
                    self.statusBar().showMessage(f'已删除标签 "{tag_name}"')
                    dialog.close()
                    break
                elif tag_info == tag_name:
                    self.tags[self.current_file].remove(tag_info)
                    self.save_tags()
                    self.statusBar().showMessage(f'已删除标签 "{tag_name}"')
                    dialog.close()
                    break
            if not self.tags[self.current_file]:
                del self.tags[self.current_file]
                self.save_tags()
        else:
            self.statusBar().showMessage('请选择一个要删除的标签')

    def showConversionError(self, error_message, format):
        if 'Pandoc未安装' in error_message:
            QMessageBox.critical(self, 'Pandoc未安装', 'Pandoc未安装，转换功能不可用。请安装Pandoc以启用转换功能.<br><br><font color="red">下载链接: <a href="https://pandoc.org/installing.html">https://pandoc.org/installing.html</a></font>', QMessageBox.Ok)
            self.statusBar().showMessage('转换失败: Pandoc未安装')
        else:
            QMessageBox.warning(self, '转换错误', error_message, QMessageBox.Ok)
            self.statusBar().showMessage('转换失败: 发生错误')

    def load_tags(self):
        try:
            with open('tags.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_tags(self):
        with open('tags.json', 'w') as f:
            json.dump(self.tags, f, indent=4)

    def setDefaultMdHandler(self):
        try:
            import winreg
            app_path = os.path.abspath(sys.argv[0])
            if app_path.endswith('.py'):
                QMessageBox.warning(self, '设置默认程序', '无法在开发模式下设置默认程序。请运行编译后的EXE文件。', QMessageBox.Ok)
                return

            # Define the application name and description
            app_name = 'MarkdownReader'
            app_description = 'Markdown Reader Application'

            # Set up the file association for .md files
            # 1. Create or open the .md key
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\.md')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'{app_name}.md')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置.md文件关联: {e}', QMessageBox.Ok)
                return

            # 2. Create or open the application key
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, app_description)
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法创建应用程序键: {e}', QMessageBox.Ok)
                return

            # 3. Set the default icon
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md\DefaultIcon')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{app_path}",0')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置默认图标: {e}', QMessageBox.Ok)
                return

            # 4. Set the shell open command
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md\shell\open\command')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{app_path}" "%1"')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置打开命令: {e}', QMessageBox.Ok)
                return

            # Notify Windows about the change
            # SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL)
            # This requires ctypes.windll.shell32.SHChangeNotify
            # For simplicity, we'll skip this for now, as it often works without it.
            # If issues arise, this can be added.

            QMessageBox.information(self, '设置默认程序', 'Markdown Reader 已成功设置为 .md 文件的默认打开程序。', QMessageBox.Ok)

        except ImportError:
            QMessageBox.critical(self, '错误', '无法导入 winreg 模块。此功能仅在 Windows 上可用。', QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'设置默认程序时发生未知错误: {e}', QMessageBox.Ok)

if __name__ == '__main__':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    app = QApplication(sys.argv)
    ex = MarkdownReader()
    ex.show()
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path) and file_path.endswith('.md'):
            ex.openFile(file_path)
    sys.exit(app.exec())
], ['\\[','\\]']],
                        processEscapes: true
                    }
                });
            </script>
            <script src="https://cdn.jsdelivr.net/npm/mermaid/dist/mermaid.min.js"></script>
            <script>mermaid.initialize({startOnLoad:true});</script>
            """
            html_content = f"<html><head>{mathjax_html}</head><body>{html_content}</body></html>"
            self.contentLoaded.emit(html_content)
        except Exception as e:
            self.contentLoaded.emit(f"<html><body><h1>加载文件出错: {str(e)}</h1></body></html>")

class ConvertThread(QThread):
    conversionFinished = Signal(str)
    conversionError = Signal(str)

    def __init__(self, input_file, output_file, format_type, resource_dir):
        super().__init__()
        self.input_file = input_file
        self.output_file = output_file
        self.format_type = format_type
        self.resource_dir = resource_dir

    def run(self):
        try:
            if getattr(sys, 'frozen', False):
                # If the application is run as a bundle, the PyInstaller bootloader
                # extends the sys module by a flag frozen=True and sets the absolute
                # path of the bundle by the _MEIPASS attribute.
                pandoc_base_path = sys._MEIPASS
            else:
                pandoc_base_path = os.getcwd()
            command = [os.path.join(pandoc_base_path, 'pandoc-3.7.0.2', 'pandoc.exe'), self.input_file, '-o', self.output_file, '--embed-resources', '--standalone', f'--resource-path={self.resource_dir}']
            result = subprocess.run(command,
                                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS,
                                    stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL,
                                    stderr=subprocess.PIPE,
                                    text=True,
                                    encoding='utf-8',
                                    errors='ignore')
            if result.returncode == 0:
                self.conversionFinished.emit(f'转换完成: {os.path.basename(self.input_file)} -> {os.path.basename(self.output_file)}')
            else:
                self.conversionError.emit(f'转换失败: Pandoc exited with code {result.returncode}\n{result.stderr}')
        except FileNotFoundError:
            self.conversionError.emit('Pandoc未安装')
        except Exception as e:
            self.conversionError.emit(f'转换过程中发生错误: {str(e)}')

class MarkdownReader(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.translator = QTranslator()
        self.tags = self.load_tags()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Markdown Reader')
        self.setGeometry(100, 100, 800, 600)
        self.setAcceptDrops(True)
        self.setup_toolbar()
        self.setup_main_layout()
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage('就绪')

    def setup_toolbar(self):
        self.toolbar = QToolBar()
        self.toolbar.setMovable(False)
        self.addToolBar(self.toolbar)

        fileButton = QPushButton('文件')
        fileButton.clicked.connect(self.showFileMenu)
        self.toolbar.addWidget(fileButton)

        tagButton = QPushButton('标签')
        tagButton.clicked.connect(self.showTagMenu)
        self.toolbar.addWidget(tagButton)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.toolbar.addWidget(spacer)

        self.searchInput = QLineEdit()
        self.searchInput.setPlaceholderText('搜索...')
        self.searchInput.returnPressed.connect(self.searchText)
        self.toolbar.addWidget(self.searchInput)

        searchButton = QPushButton('搜索')
        searchButton.clicked.connect(self.searchText)
        self.toolbar.addWidget(searchButton)

    def setup_main_layout(self):
        layout = QVBoxLayout()
        self.webView = QWebEngineView()
        layout.addWidget(self.webView, 1)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def openFile(self, fname=None):
        if not fname:
            fname, _ = QFileDialog.getOpenFileName(self, '打开Markdown文件', '', 'Markdown文件 (*.md)')
        if fname:
            self.current_file = fname
            self.statusBar().showMessage(f'正在打开: {os.path.basename(fname)}...')
            self.setEnabled(False)
            self.loader_thread = FileLoaderThread(fname)
            self.loader_thread.contentLoaded.connect(lambda html: self.webView.setHtml(html, QUrl.fromLocalFile(fname)))
            self.loader_thread.progress.connect(self.statusBar().showMessage)
            self.loader_thread.finished.connect(lambda: [self.statusBar().showMessage(f'已打开: {os.path.basename(fname)}'), self.setEnabled(True)])
            self.loader_thread.start()

    def showFileMenu(self):
        menu = QMenu(self)
        openAction = QAction('打开', self)
        openAction.triggered.connect(self.openFile)
        menu.addAction(openAction)

        saveDocxAction = QAction('保存为DOCX', self)
        saveDocxAction.triggered.connect(lambda: self.convertTo('docx'))
        menu.addAction(saveDocxAction)

        saveHtmlAction = QAction('保存为HTML', self)
        saveHtmlAction.triggered.connect(lambda: self.convertTo('html'))
        menu.addAction(saveHtmlAction)

        menu.addSeparator()

        setDefaultAction = QAction('设置为默认Markdown阅读器', self)
        setDefaultAction.triggered.connect(self.setDefaultMdHandler)
        menu.addAction(setDefaultAction)

        menu.exec(self.mapToGlobal(self.toolbar.geometry().bottomLeft()))

    def searchText(self):
        search_term = self.searchInput.text()
        if search_term:
            self.webView.findText(search_term)

    def showTagMenu(self):
        menu = QMenu(self)
        addTagAction = QAction('添加标签', self)
        addTagAction.triggered.connect(self.addTag)
        menu.addAction(addTagAction)

        viewTagsAction = QAction('查看标签', self)
        viewTagsAction.triggered.connect(self.viewTags)
        menu.addAction(viewTagsAction)

        deleteTagAction = QAction('删除标签', self)
        deleteTagAction.triggered.connect(self.deleteTag)
        menu.addAction(deleteTagAction)

        menu.exec(self.mapToGlobal(self.toolbar.geometry().bottomLeft()))

    def searchPrevious(self):
        search_term = self.searchInput.text()
        if not search_term:
            QMessageBox.warning(self, '搜索', '请输入搜索词', QMessageBox.Ok)
            return

        if not hasattr(self, 'last_search_term') or self.last_search_term != search_term:
            self.searchText()

        flags = QWebEnginePage.FindFlag.FindBackward
        self.webView.findText(search_term, flags, lambda found: self.statusBar().showMessage('找到上一个匹配项' if found else '未找到上一个匹配项'))
        self.last_search_term = search_term

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            pos = event.position().toPoint()
            web_view_rect = self.webView.geometry()
            if web_view_rect.contains(pos):
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.endswith('.md'):
                self.openFile(file_path)
                break

    def addTag(self):
        tag, ok = QInputDialog.getText(self, '添加标签', '输入标签名称:')
        if ok and tag:
            if self.current_file:
                if self.current_file not in self.tags:
                    self.tags[self.current_file] = []
                self.webView.page().runJavaScript("window.scrollY", 0, lambda result: self.storeTagWithPosition(tag, result))
            else:
                self.statusBar().showMessage('请先打开一个文件')

    def viewTags(self):
        if not self.tags:
            QMessageBox.information(self, '标签', '没有标签', QMessageBox.Ok)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('标签列表')
        layout = QVBoxLayout()

        listWidget = QListWidget()
        for file, tags in self.tags.items():
            for tag_info in tags:
                if isinstance(tag_info, dict):
                    tag_name = tag_info.get('name', '未知标签')
                    position = tag_info.get('position', '未知位置')
                    listWidget.addItem(f"{os.path.basename(file)}: {tag_name} (位置: {position})")
                else:
                    listWidget.addItem(f"{os.path.basename(file)}: {tag_info}")
        layout.addWidget(listWidget)

        listWidget.itemDoubleClicked.connect(lambda item: self.jumpToTagPosition(item, dialog))

        closeButton = QPushButton('关闭')
        closeButton.clicked.connect(dialog.close)
        layout.addWidget(closeButton)

        jumpButton = QPushButton('跳转到标签位置')
        jumpButton.clicked.connect(lambda: self.jumpToTagPosition(listWidget.currentItem(), dialog))
        layout.addWidget(jumpButton)

        dialog.setLayout(layout)
        dialog.exec()

    def storeTagWithPosition(self, tag, scrollY):
        tag_info = {'name': tag, 'position': scrollY}
        if tag_info not in self.tags[self.current_file]:
            self.tags[self.current_file].append(tag_info)
            self.save_tags()
            self.statusBar().showMessage(f'已添加标签 "{tag}" 到当前文件，位置: {scrollY}')
        else:
            self.statusBar().showMessage(f'标签 "{tag}" 已存在于当前文件')

    def jumpToTagPosition(self, item, dialog):
        if item:
            text = item.text()
            start_idx = text.find('(位置: ')
            if start_idx != -1:
                position_str = text[start_idx + 7:].rstrip(')')
                try:
                    position = int(position_str)
                    self.webView.page().runJavaScript(f"window.scrollTo(0, {position});", 0, lambda _: None)
                    dialog.close()
                    self.statusBar().showMessage(f'已跳转到标签位置: {position}')
                except ValueError:
                    self.statusBar().showMessage('无法解析标签位置')
            else:
                self.statusBar().showMessage('无法找到标签位置信息')
        else:
            self.statusBar().showMessage('请选择一个标签')

    def convertTo(self, format):
        if not self.current_file:
            return

        base_name = os.path.basename(self.current_file)
        base_name_without_ext = os.path.splitext(base_name)[0]
        default_save_name = f"{base_name_without_ext}.{format}"

        output_file, _ = QFileDialog.getSaveFileName(self, f'保存为{format.upper()}', default_save_name, f'{format.upper()}文件 (*.{format})')
        if output_file:
            self.statusBar().showMessage(f'转换中: {base_name} -> {format.upper()}')
            self.setEnabled(False)
            resource_dir = os.path.dirname(self.current_file)
            self.convert_thread = ConvertThread(self.current_file, output_file, format, resource_dir)
            self.convert_thread.conversionFinished.connect(lambda msg: [self.statusBar().showMessage(msg), self.setEnabled(True)])
            self.convert_thread.conversionError.connect(lambda err: [self.showConversionError(err, format), self.setEnabled(True)])
            self.convert_thread.start()

    def deleteTag(self):
        if not self.tags or not self.current_file or self.current_file not in self.tags:
            QMessageBox.information(self, '删除标签', '当前文件没有标签', QMessageBox.Ok)
            return

        dialog = QDialog(self)
        dialog.setWindowTitle('删除标签')
        layout = QVBoxLayout()

        listWidget = QListWidget()
        for tag_info in self.tags[self.current_file]:
            if isinstance(tag_info, dict):
                tag_name = tag_info.get('name', '未知标签')
                position = tag_info.get('position', '未知位置')
                listWidget.addItem(f"{tag_name} (位置: {position})")
            else:
                listWidget.addItem(tag_info)
        layout.addWidget(listWidget)

        deleteButton = QPushButton('删除')
        deleteButton.clicked.connect(lambda: self.removeTag(listWidget.currentItem(), dialog))
        layout.addWidget(deleteButton)

        closeButton = QPushButton('关闭')
        closeButton.clicked.connect(dialog.close)
        layout.addWidget(closeButton)

        dialog.setLayout(layout)
        dialog.exec()

    def removeTag(self, item, dialog):
        if item:
            text = item.text()
            start_idx = text.find('(位置: ')
            tag_name = text.split(' (位置: ')[0] if start_idx != -1 else text
            for tag_info in self.tags[self.current_file][:]:
                if isinstance(tag_info, dict) and tag_info.get('name') == tag_name:
                    self.tags[self.current_file].remove(tag_info)
                    self.save_tags()
                    self.statusBar().showMessage(f'已删除标签 "{tag_name}"')
                    dialog.close()
                    break
                elif tag_info == tag_name:
                    self.tags[self.current_file].remove(tag_info)
                    self.save_tags()
                    self.statusBar().showMessage(f'已删除标签 "{tag_name}"')
                    dialog.close()
                    break
            if not self.tags[self.current_file]:
                del self.tags[self.current_file]
                self.save_tags()
        else:
            self.statusBar().showMessage('请选择一个要删除的标签')

    def showConversionError(self, error_message, format):
        if 'Pandoc未安装' in error_message:
            QMessageBox.critical(self, 'Pandoc未安装', 'Pandoc未安装，转换功能不可用。请安装Pandoc以启用转换功能.<br><br><font color="red">下载链接: <a href="https://pandoc.org/installing.html">https://pandoc.org/installing.html</a></font>', QMessageBox.Ok)
            self.statusBar().showMessage('转换失败: Pandoc未安装')
        else:
            QMessageBox.warning(self, '转换错误', error_message, QMessageBox.Ok)
            self.statusBar().showMessage('转换失败: 发生错误')

    def load_tags(self):
        try:
            with open('tags.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_tags(self):
        with open('tags.json', 'w') as f:
            json.dump(self.tags, f, indent=4)

    def setDefaultMdHandler(self):
        try:
            import winreg
            app_path = os.path.abspath(sys.argv[0])
            if app_path.endswith('.py'):
                QMessageBox.warning(self, '设置默认程序', '无法在开发模式下设置默认程序。请运行编译后的EXE文件。', QMessageBox.Ok)
                return

            # Define the application name and description
            app_name = 'MarkdownReader'
            app_description = 'Markdown Reader Application'

            # Set up the file association for .md files
            # 1. Create or open the .md key
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, r'Software\Classes\.md')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'{app_name}.md')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置.md文件关联: {e}', QMessageBox.Ok)
                return

            # 2. Create or open the application key
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, app_description)
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法创建应用程序键: {e}', QMessageBox.Ok)
                return

            # 3. Set the default icon
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md\DefaultIcon')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{app_path}",0')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置默认图标: {e}', QMessageBox.Ok)
                return

            # 4. Set the shell open command
            try:
                key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, fr'Software\Classes\{app_name}.md\shell\open\command')
                winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{app_path}" "%1"')
                winreg.CloseKey(key)
            except Exception as e:
                QMessageBox.critical(self, '错误', f'无法设置打开命令: {e}', QMessageBox.Ok)
                return

            # Notify Windows about the change
            # SHChangeNotify(SHCNE_ASSOCCHANGED, SHCNF_IDLIST, NULL, NULL)
            # This requires ctypes.windll.shell32.SHChangeNotify
            # For simplicity, we'll skip this for now, as it often works without it.
            # If issues arise, this can be added.

            QMessageBox.information(self, '设置默认程序', 'Markdown Reader 已成功设置为 .md 文件的默认打开程序。', QMessageBox.Ok)

        except ImportError:
            QMessageBox.critical(self, '错误', '无法导入 winreg 模块。此功能仅在 Windows 上可用。', QMessageBox.Ok)
        except Exception as e:
            QMessageBox.critical(self, '错误', f'设置默认程序时发生未知错误: {e}', QMessageBox.Ok)

if __name__ == '__main__':
    ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
    app = QApplication(sys.argv)
    ex = MarkdownReader()
    ex.show()
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if os.path.exists(file_path) and file_path.endswith('.md'):
            ex.openFile(file_path)
    sys.exit(app.exec())

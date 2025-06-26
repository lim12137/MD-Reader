#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

def test_pandoc_path():
    print("测试pandoc路径查找逻辑...")
    print(f"sys.executable: {sys.executable}")
    print(f"sys.frozen: {getattr(sys, 'frozen', False)}")
    print(f"__file__: {__file__}")
    
    # 模拟main.py中的逻辑
    if getattr(sys, 'frozen', False):
        # 打包后的环境，pandoc在_internal目录下
        pandoc_dir = os.path.join(os.path.dirname(sys.executable), "_internal", "pandoc-2.14.0.3")
        print("使用打包后的路径逻辑")
    else:
        # 开发环境，pandoc在项目根目录下
        pandoc_dir = os.path.join(os.path.dirname(__file__), "..", "pandoc-2.14.0.3")
        print("使用开发环境的路径逻辑")
    
    pandoc_path = os.path.join(pandoc_dir, "pandoc.exe")
    
    print(f"pandoc_dir: {pandoc_dir}")
    print(f"pandoc_path: {pandoc_path}")
    print(f"pandoc存在: {os.path.exists(pandoc_path)}")
    
    if os.path.exists(pandoc_path):
        print("✅ pandoc路径正确！")
        # 测试pandoc是否可以执行
        try:
            import subprocess
            result = subprocess.run([pandoc_path, "--version"], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                print("✅ pandoc可以正常执行！")
                print(f"pandoc版本信息: {result.stdout.split()[1] if len(result.stdout.split()) > 1 else 'unknown'}")
            else:
                print(f"❌ pandoc执行失败，返回码: {result.returncode}")
                print(f"错误信息: {result.stderr}")
        except Exception as e:
            print(f"❌ pandoc执行测试失败: {e}")
    else:
        print("❌ pandoc路径不正确！")

if __name__ == "__main__":
    test_pandoc_path()

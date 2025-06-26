#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import sys

def debug_pandoc():
    pandoc_path = os.path.abspath(r"dist\main\_internal\pandoc-2.14.0.3\pandoc.exe")
    
    print(f"Pandoc路径: {pandoc_path}")
    print(f"Pandoc存在: {os.path.exists(pandoc_path)}")
    
    if not os.path.exists(pandoc_path):
        print("❌ Pandoc文件不存在")
        return
    
    # 获取文件信息
    stat = os.stat(pandoc_path)
    print(f"文件大小: {stat.st_size} 字节")
    print(f"文件权限: {oct(stat.st_mode)}")
    
    # 测试不同的命令
    commands = [
        [pandoc_path, "--version"],
        [pandoc_path, "--help"],
        [pandoc_path]
    ]
    
    for i, cmd in enumerate(commands):
        print(f"\n=== 测试命令 {i+1}: {' '.join(cmd)} ===")
        try:
            # 使用不同的方法执行
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                encoding='utf-8',
                errors='replace'
            )
            
            print(f"返回码: {result.returncode}")
            print(f"标准输出长度: {len(result.stdout)}")
            print(f"错误输出长度: {len(result.stderr)}")
            
            if result.stdout:
                print(f"标准输出前200字符: {repr(result.stdout[:200])}")
            if result.stderr:
                print(f"错误输出前200字符: {repr(result.stderr[:200])}")
                
        except subprocess.TimeoutExpired:
            print("❌ 命令超时")
        except Exception as e:
            print(f"❌ 执行异常: {e}")
    
    # 检查依赖
    print(f"\n=== 检查系统依赖 ===")
    
    # 检查Visual C++运行时
    vcredist_paths = [
        r"C:\Windows\System32\vcruntime140.dll",
        r"C:\Windows\System32\msvcp140.dll",
        r"C:\Windows\System32\vcruntime140_1.dll"
    ]
    
    for dll_path in vcredist_paths:
        exists = os.path.exists(dll_path)
        print(f"{dll_path}: {'存在' if exists else '不存在'}")
    
    # 检查打包目录中的DLL
    internal_dir = os.path.dirname(pandoc_path).replace("pandoc-2.14.0.3", "")
    print(f"\n打包目录: {internal_dir}")
    
    dll_files = []
    if os.path.exists(internal_dir):
        for file in os.listdir(internal_dir):
            if file.lower().endswith('.dll'):
                dll_files.append(file)
    
    print(f"打包目录中的DLL文件: {dll_files}")

if __name__ == "__main__":
    debug_pandoc()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import subprocess
import os
import sys

def test_pandoc():
    pandoc_path = r"dist\main\_internal\pandoc-2.14.0.3\pandoc.exe"
    input_file = r"test\test.md"
    output_file = r"test\test_output.docx"
    
    print(f"pandoc路径: {pandoc_path}")
    print(f"pandoc存在: {os.path.exists(pandoc_path)}")
    print(f"输入文件: {input_file}")
    print(f"输入文件存在: {os.path.exists(input_file)}")
    
    if not os.path.exists(pandoc_path):
        print("❌ pandoc不存在")
        return
    
    if not os.path.exists(input_file):
        print("❌ 输入文件不存在")
        return
    
    # 删除之前的输出文件
    if os.path.exists(output_file):
        os.remove(output_file)
        print(f"删除旧的输出文件: {output_file}")
    
    # 测试pandoc版本
    print("\n测试pandoc版本...")
    try:
        result = subprocess.run([pandoc_path, "--version"], 
                              capture_output=True, text=True, timeout=10)
        print(f"版本命令返回码: {result.returncode}")
        if result.returncode == 0:
            print(f"pandoc版本: {result.stdout.split()[1]}")
        else:
            print(f"版本命令错误: {result.stderr}")
    except Exception as e:
        print(f"版本测试异常: {e}")
    
    # 测试转换
    print("\n测试转换...")
    command = [pandoc_path, input_file, "-o", output_file, "--standalone"]
    print(f"执行命令: {' '.join(command)}")
    
    try:
        result = subprocess.run(command, 
                              capture_output=True, text=True, timeout=30)
        print(f"转换命令返回码: {result.returncode}")
        print(f"标准输出: '{result.stdout}'")
        print(f"错误输出: '{result.stderr}'")
        
        if result.returncode == 0:
            if os.path.exists(output_file):
                size = os.path.getsize(output_file)
                print(f"✅ 转换成功！输出文件大小: {size} 字节")
            else:
                print("❌ 转换命令成功但输出文件不存在")
        else:
            print("❌ 转换失败")
            
    except Exception as e:
        print(f"转换测试异常: {e}")

if __name__ == "__main__":
    test_pandoc()

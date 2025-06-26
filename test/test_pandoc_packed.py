#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import subprocess

def test_pandoc_conversion():
    """测试打包后的pandoc转换功能"""
    print("测试打包后的pandoc转换功能...")
    
    # 模拟打包环境
    executable_dir = os.path.abspath("dist/main")
    executable_path = os.path.join(executable_dir, "main.exe")
    
    print(f"可执行文件路径: {executable_path}")
    print(f"可执行文件存在: {os.path.exists(executable_path)}")
    
    # 检查pandoc路径
    pandoc_dir = os.path.join(executable_dir, "_internal", "pandoc-2.14.0.3")
    pandoc_path = os.path.join(pandoc_dir, "pandoc.exe")
    
    print(f"pandoc目录: {pandoc_dir}")
    print(f"pandoc路径: {pandoc_path}")
    print(f"pandoc存在: {os.path.exists(pandoc_path)}")
    
    if not os.path.exists(pandoc_path):
        print("❌ pandoc文件不存在！")
        return False
    
    # 测试pandoc版本
    try:
        result = subprocess.run([pandoc_path, "--version"], 
                              capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            print("✅ pandoc可以正常执行！")
            version_line = result.stdout.split('\n')[0]
            print(f"pandoc版本: {version_line}")
        else:
            print(f"❌ pandoc执行失败，返回码: {result.returncode}")
            print(f"错误信息: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ pandoc执行测试失败: {e}")
        return False
    
    # 测试转换功能
    test_md = "test/test.md"
    test_output = "test/test_output.docx"
    
    if not os.path.exists(test_md):
        print(f"❌ 测试文件不存在: {test_md}")
        return False
    
    print(f"测试转换: {test_md} -> {test_output}")
    
    try:
        # 模拟main.py中的转换命令
        resource_dir = os.path.dirname(os.path.abspath(test_md))
        command = [pandoc_path, test_md, '-o', test_output, 
                  '--embed-resources', '--standalone', f'--resource-path={resource_dir}']
        
        print(f"执行命令: {' '.join(command)}")
        
        result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ 转换成功！")
            if os.path.exists(test_output):
                print(f"✅ 输出文件已生成: {test_output}")
                file_size = os.path.getsize(test_output)
                print(f"文件大小: {file_size} 字节")
                return True
            else:
                print("❌ 输出文件未生成")
                return False
        else:
            print(f"❌ 转换失败，返回码: {result.returncode}")
            print(f"标准输出: {result.stdout}")
            print(f"错误输出: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ 转换测试失败: {e}")
        return False

if __name__ == "__main__":
    success = test_pandoc_conversion()
    if success:
        print("\n🎉 所有测试通过！pandoc功能正常。")
    else:
        print("\n❌ 测试失败！需要进一步调试。")

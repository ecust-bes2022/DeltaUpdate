#!/usr/bin/env python3
import os
import sys

def main():
    """运行客户端"""
    # 获取脚本所在目录
    client_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 切换到客户端目录
    os.chdir(client_dir)
    
    # 运行客户端
    cmd = "python client.py"
    print(f"执行命令: {cmd}")
    print(f"工作目录: {os.getcwd()}")
    os.system(cmd)

if __name__ == "__main__":
    main() 
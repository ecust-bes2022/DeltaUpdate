#!/usr/bin/env python3
import os
import sys
import json

def main():
    """运行服务器"""
    # 获取脚本所在目录
    server_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 切换到服务器目录
    os.chdir(server_dir)
    
    # 加载配置
    with open('server_config.json', 'r') as f:
        config = json.load(f)
        server_config = config['SERVER_CONFIG']
    
    # 运行服务器
    cmd = f"python -m uvicorn server:app --host {server_config['host']} --port {server_config['port']}"
    print(f"执行命令: {cmd}")
    print(f"工作目录: {os.getcwd()}")
    os.system(cmd)

if __name__ == "__main__":
    main() 
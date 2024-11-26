#!/usr/bin/env python3
import os
import sys
import requests
import json
from tools.version_manager import VersionManager

# 加载配置
with open(os.path.join(os.path.dirname(__file__), 'server_config.json'), 'r') as f:
    config = json.load(f)
    SERVER_CONFIG = config['SERVER_CONFIG']
    APP_CONFIG = config['APP_CONFIG']

def reload_server_config():
    """通知服务器重新加载配置"""
    try:
        # 添加超时设置
        response = requests.get(
            f"http://localhost:{SERVER_CONFIG['port']}/reload_config",
            timeout=5  # 5秒超时
        )
        if response.status_code == 200:
            print("服务器配置已重新加载")
            return True
        else:
            print(f"服务器配置重新加载失败: HTTP {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("警告: 无法连接到服务器，请确保服务器正在运行")
        return False
    except Exception as e:
        print(f"通知服务器重新加载配置失败: {str(e)}")
        return False

def main():
    """生成新版本"""
    try:
        # 获取脚本所在目录
        server_dir = os.path.dirname(os.path.abspath(__file__))
        os.chdir(server_dir)
        
        # 创建版本管理器实例
        manager = VersionManager()
        
        # 从配置中获取应用信息
        version = APP_CONFIG['version']
        app_path = APP_CONFIG['app_path']
        description = APP_CONFIG['description']
        
        # 检查应用文件是否存在
        if not os.path.exists(app_path):
            raise FileNotFoundError(f"应用文件不存在: {app_path}")
        
        # 添加新版本
        print(f"正在添加版本 {version}...")
        print(f"应用路径: {app_path}")
        print(f"版本描述: {description}")
        
        manager.add_version(version, app_path, description)
        
        print("\n版本添加成功！")
        print(f"版本号: {version}")
        print(f"描述: {description}")
        
        # 重新加载服务器配置
        print("\n正在重新加载服务器配置...")
        if reload_server_config():
            print("服务器已更新到新版本")
        else:
            print("警告: 服务器配置重新加载失败，可能需要手动重启服务器")
        
    except Exception as e:
        print(f"添加版本失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
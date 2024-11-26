import os
import sys
import logging
from client.client import UpdateClient
from PySide6.QtCore import QObject, Signal
import json
import platform

class UpdateManager(QObject):
    # 定义信号
    update_available = Signal(str, str)  # 版本号, 更新说明
    update_progress = Signal(str, int)   # 描述, 进度
    update_finished = Signal(bool, str)  # 成功/失败, 消息
    
    def __init__(self):
        super().__init__()
        
        # 加载配置
        with open(os.path.join(os.path.dirname(__file__), 'client', 'client_config.json'), 'r') as f:
            self.config = json.load(f)
            self.server_url = f"{self.config['SERVER']['URL']}:{self.config['SERVER']['PORT']}"
            self.app_name = self.config['APP_NAME']
        
        # 动态获取系统类型
        self.system_type = platform.system()
        self.client = UpdateClient()
    
    def check_update(self):
        """检查更新"""
        try:
            update_info = self.client.check_for_updates()
            if update_info:
                version = update_info['latest_version']
                desc = update_info['versions'][version].get('description', '')
                self.update_available.emit(version, desc)
                return update_info
            return None
        except Exception as e:
            self.update_finished.emit(False, f"检查更新失败: {str(e)}")
            return None
    
    def do_update(self, update_info):
        """执行更新"""
        try:
            # Windows系统检查
            if self.system_type == 'Windows':
                pid = self.client.check_app_running()
                if pid:
                    self.update_finished.emit(False, "请先关闭应用后再更新")
                    return False
            
            # 执行更新
            version = update_info['latest_version']
            self.update_progress.emit("正在更新...", 0)
            
            success = self.client.download_update(update_info)
            
            if success:
                self.update_finished.emit(True, f"更新到版本 {version} 成功")
            else:
                self.update_finished.emit(False, "更新失败")
            
            return success
            
        except Exception as e:
            self.update_finished.emit(False, f"更新失败: {str(e)}")
            return False 
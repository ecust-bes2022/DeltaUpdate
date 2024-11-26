import sys
import os
import json
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QMessageBox, QPushButton, 
    QVBoxLayout, QWidget, QProgressBar, QLabel
)
from PySide6.QtCore import QThread, Signal, QTimer
from update_manager import UpdateManager
import atexit
import multiprocessing
import subprocess
import platform

# 加载配置
with open(os.path.join(os.path.dirname(__file__), 'client', 'client_config.json'), 'r') as f:
    config = json.load(f)
    SERVER_URL = f"{config['SERVER']['URL']}:{config['SERVER']['PORT']}"
    APP_NAME = config['APP_NAME']

# 动态获取系统类型
SYSTEM_TYPE = platform.system()

class UpdateWorker(QThread):
    progress = Signal(str, int)  # 进度信号
    
    def __init__(self, update_manager, update_info):
        super().__init__()
        self.manager = update_manager
        self.update_info = update_info
    
    def run(self):
        try:
            success = self.manager.do_update(self.update_info)
            if success:
                self.manager.update_finished.emit(True, "更新完成")
            else:
                self.manager.update_finished.emit(False, "更新失败")
        except Exception as e:
            self.manager.update_finished.emit(False, f"更新出错: {str(e)}")
        finally:
            self.quit()  # 确保线程结束

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} - 测试界面")
        self.setMinimumSize(400, 300)
        self.updating = False
        self.setup_ui()
        self.setup_updater()
        
        # 添加资源清理
        atexit.register(self.cleanup_resources)
    
    def setup_ui(self):
        """设置界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 版本信息标签
        self.version_label = QLabel(f"当前版本: {self.get_current_version()}")
        layout.addWidget(self.version_label)
        
        # 检查更新按钮
        check_update_btn = QPushButton("检查更新")
        check_update_btn.clicked.connect(self.check_for_updates)
        layout.addWidget(check_update_btn)
        
        # 进度条（默认隐藏）
        self.progress_bar = QProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # 状态标签
        self.status_label = QLabel()
        layout.addWidget(self.status_label)
        
        # 添加一些空白
        layout.addStretch()
        
    def get_current_version(self):
        """获取当前版本"""
        try:
            with open(os.path.join("client", "current_version", "version.json"), "r") as f:
                data = json.load(f)
                return data.get("version", "未知")
        except:
            return "未知"
        
    def setup_updater(self):
        """设置更新管理器"""
        self.update_manager = UpdateManager()
        
        # 连接信号
        self.update_manager.update_available.connect(self.on_update_available)
        self.update_manager.update_progress.connect(self.on_update_progress)
        self.update_manager.update_finished.connect(self.on_update_finished)
        
    def check_for_updates(self):
        """检查更新"""
        self.status_label.setText("正在检查更新...")
        update_info = self.update_manager.check_update()
        if not update_info:
            self.status_label.setText("当前已是最新版本")
            QMessageBox.information(self, "检查更新", "当前已是最新版本")
    
    def on_update_available(self, version, desc):
        """有更新可用"""
        self.status_label.setText(f"发现新版本: {version}")
        
        # 避免重复弹窗
        if hasattr(self, 'updating') and self.updating:
            return
        
        reply = QMessageBox.question(
            self,
            "发现新版本",
            f"发现新版本 {version}\n\n更新说明:\n{desc}\n\n"
            f"注意: 更新需要关闭当前应用，更新完成后将自动重启。\n\n是否现在更新？",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.updating = True  # 标记正在更新
            # 显示进度条
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            
            # 在新线程中执行更新
            self.update_thread = UpdateWorker(
                self.update_manager,
                self.update_manager.check_update()
            )
            self.update_thread.start()
    
    def on_update_progress(self, desc, progress):
        """更新进度"""
        self.status_label.setText(desc)
        self.progress_bar.setValue(progress)
    
    def on_update_finished(self, success, message):
        """更新完成"""
        try:
            self.progress_bar.hide()
            if success and not self.updating:
                self.updating = True
                
                # 先清理资源
                if hasattr(self, 'update_thread'):
                    self.update_thread.quit()
                    self.update_thread.wait()
                
                # 显示更新完成息
                QMessageBox.information(
                    self, 
                    "更新完成",
                    "更新已完成，请手动重启应用以应用更改。",
                    QMessageBox.Ok
                )
                
                # 直接退出应用
                QApplication.quit()
                
            elif not success:
                self.updating = False
                self.status_label.setText("更新失败")
                QMessageBox.warning(self, "更新失败", message)
                
        except Exception as e:
            print(f"处理更新完成时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def do_restart(self):
        """执行重启"""
        try:
            print("准备重启应用...")
            current_dir = os.path.dirname(os.path.abspath(__file__))
            python_exe = sys.executable
            app_path = os.path.join(current_dir, 'main.py')
            
            # 启动新实例
            subprocess.Popen(
                [python_exe, app_path],
                cwd=current_dir,
                start_new_session=True  # 在新会话中启动
            )
            
            # 使用 QTimer 确保新实例启动后再退出
            QTimer.singleShot(1000, self.force_quit)
            
        except Exception as e:
            print(f"重启失败: {str(e)}")
            import traceback
            traceback.print_exc()

    def force_quit(self):
        """强制退出应用"""
        print("退出当前实例...")
        QApplication.quit()
        sys.exit(0)  # 确保完全退出

    def restart_application(self):
        """重启应用"""
        try:
            self.cleanup_resources()  # 确保在重启前清理资源
            os.execv(sys.executable, [sys.executable] + sys.argv)
        except Exception as e:
            print(f"重启应用时出错: {str(e)}")
            sys.exit(0)  # 如果重启失败，直接退出
    
    def cleanup_resources(self):
        """清理资源"""
        try:
            # 确保所有线程和进程都已结束
            if hasattr(self, 'update_thread'):
                self.update_thread.quit()
                self.update_thread.wait()
            
            # 清理其他���源
            for p in multiprocessing.active_children():
                p.terminate()
                p.join()
        except Exception as e:
            print(f"清理资源时出错: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件"""
        try:
            # 确保清理所有资源
            if hasattr(self, 'update_thread'):
                self.update_thread.quit()
                self.update_thread.wait()
            event.accept()
        except Exception as e:
            print(f"关闭窗口时出错: {str(e)}")
            event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
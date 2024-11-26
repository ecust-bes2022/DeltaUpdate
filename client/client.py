import requests
import os
import json
import hashlib
import shutil
import logging
from tqdm import tqdm
import time
import platform
import psutil
import bsdiff4
import sys
from datetime import datetime

# 加载配置
with open(os.path.join(os.path.dirname(__file__), 'client_config.json'), 'r') as f:
    config = json.load(f)
    SERVER_URL = f"{config['SERVER']['URL']}:{config['SERVER']['PORT']}"
    APP_NAME = config['APP_NAME']
    SYSTEM_TYPE = platform.system()  # 返回 'Darwin', 'Windows' 或 'Linux'

class UpdateClient:
    def __init__(self):
        self.server_url = SERVER_URL
        self.current_dir = os.path.join(os.path.dirname(__file__), 'current_version')
        self.backup_dir = os.path.join(os.path.dirname(__file__), 'backup')
        self.temp_dir = os.path.join(os.path.dirname(__file__), 'temp')
        self.config_file = os.path.join(os.path.dirname(__file__), 'client_config.json')
        
        # 配置日志
        log_dir = os.path.join(os.path.dirname(__file__), 'logs')
        os.makedirs(log_dir, exist_ok=True)
        logging.basicConfig(
            filename=os.path.join(log_dir, 'client.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # 确保必要的目录存在
        os.makedirs(self.current_dir, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # 加载当前版本号
        self.current_version = self.load_current_version()
        self.log_time = lambda: datetime.now().strftime('[%Y-%m-%d %H:%M:%S]')

    def load_current_version(self):
        """加载当前版本号"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                return config.get('CURRENT_VERSION', '1.0.0')
        except Exception as e:
            logging.error(f"加载版本号失败: {str(e)}")
            return '1.0.0'

    def save_current_version(self, version):
        """保存当前版本号"""
        try:
            # 读取现有配置
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # 更新版本号
            config['CURRENT_VERSION'] = version
            
            # 保存配置
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=4)
                
            logging.info(f"已更新版本号到: {version}")
            
        except Exception as e:
            logging.error(f"保存版本号失败: {str(e)}")
            raise  # 抛出异常以便上层处理

    def get_file_md5(self, file_path):
        """计算文件的MD5值"""
        try:
            md5_hash = hashlib.md5()
            with open(file_path, "rb") as f:
                # 使用更大的缓冲区
                for chunk in iter(lambda: f.read(8192), b""):
                    md5_hash.update(chunk)
            md5_value = md5_hash.hexdigest()
            self.print_log(f"计算的MD5值: {md5_value}")  # 添加调试输出
            return md5_value
        except Exception as e:
            logging.error(f"计算MD5失败: {str(e)}")
            raise

    def backup_current_version(self):
        """备份当前版本"""
        # 创建新的备份
        backup_path = os.path.join(self.backup_dir, f"backup_{self.current_version}_{int(time.time())}")
        os.makedirs(backup_path, exist_ok=True)
        
        src_file = os.path.join(self.current_dir, APP_NAME)
        if os.path.exists(src_file):
            shutil.copy2(
                src_file,
                os.path.join(backup_path, APP_NAME)
            )
        
        logging.info(f"已备份当前版本到: {backup_path}")
        
        # 清理旧备份
        self.cleanup_old_backups()
        
        return backup_path

    def cleanup_old_backups(self, max_backups=10):
        """清理旧的备份，只保留最近的几个版本"""
        try:
            # 获取所有备份目录
            backups = []
            for item in os.listdir(self.backup_dir):
                item_path = os.path.join(self.backup_dir, item)
                if os.path.isdir(item_path) and item.startswith('backup_'):
                    # 获取备份时间戳
                    timestamp = int(item.split('_')[-1])
                    backups.append((timestamp, item_path))
            
            # 按时间戳排序
            backups.sort(reverse=True)  # 最新的在前面
            
            # 如果备份数量超过限制，删除旧的备份
            if len(backups) > max_backups:
                for _, backup_path in backups[max_backups:]:
                    try:
                        shutil.rmtree(backup_path)
                        self.print_log(f"已删除旧备份: {backup_path}")
                    except Exception as e:
                        logging.error(f"删除旧备份失败 {backup_path}: {str(e)}")
                
                remaining = len(backups) - len(backups[max_backups:])
                self.print_log(f"已清理旧备份，当前保留 {remaining} 个最新备份")
            
        except Exception as e:
            logging.error(f"清理旧备份失败: {str(e)}")

    def restore_from_backup(self, backup_path):
        """从备份恢复"""
        try:
            for file in os.listdir(backup_path):
                shutil.copy2(
                    os.path.join(backup_path, file),
                    os.path.join(self.current_dir, file)
                )
            logging.info("已从备份恢复")
            return True
        except Exception as e:
            logging.error(f"恢复备份失败: {str(e)}")
            self.print_log(f"警告: 恢复备份失败: {str(e)}")
            return False

    def version_compare(self, v1, v2):
        """比较两个版本号"""
        def parse_version(v):
            # 将版本号分割为主版本号、次版本号和修订号
            parts = v.split('.')
            # 确保有三个部分，不足的补0
            while len(parts) < 3:
                parts.append('0')
            # 转换为整数元组
            return tuple(map(int, parts))
        
        # 比较版本号元组
        return parse_version(v1) > parse_version(v2)

    def check_for_updates(self):
        """检查是否��更新可用"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.print_log(f"正在检查更新，连接地址: {self.server_url}")
            response = requests.get(f"{self.server_url}/check_update")
            version_info = response.json()
            
            self.print_log(f"当前版本: {self.current_version}")
            
            # 格式化显示服务器返回信息
            latest_version = version_info['latest_version']
            latest_desc = version_info['versions'][latest_version].get('description', '无')
            self.print_log(f"服务器版本信息:")
            self.print_log(f"最新版本: {latest_version}")
            self.print_log(f"更新说明: {latest_desc}")
            
            if self.version_compare(latest_version, self.current_version):
                self.print_log(f"发现新版本: {latest_version}")
                return version_info
            else:
                self.print_log(f"当前已是最新版本")
                return None
            
        except Exception as e:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.print_log(f"检查更新失败: {str(e)}")
            return None

    def download_with_resume(self, url, local_file, desc="下载文件"):
        """支持断点续传的下载"""
        temp_file = os.path.join(self.temp_dir, os.path.basename(local_file) + '.temp')
        
        # 获取已下载的文件大小
        if os.path.exists(temp_file):
            resume_size = os.path.getsize(temp_file)
            headers = {'Range': f'bytes={resume_size}-'}
        else:
            resume_size = 0
            headers = {}
        
        # 发起请求
        response = requests.get(url, stream=True, headers=headers)
        
        # 获取文件总大小
        if 'Content-Range' in response.headers:
            total_size = int(response.headers['Content-Range'].split('/')[-1])
        else:
            total_size = int(response.headers.get('content-length', 0))
        
        # 创建或追加模式打开文件
        mode = 'ab' if resume_size > 0 else 'wb'
        with open(temp_file, mode) as f:
            with tqdm(
                total=total_size,
                initial=resume_size,
                unit='B',
                unit_scale=True,
                desc=desc
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
        
        # 下载完成后移动到最终位置
        shutil.move(temp_file, local_file)
        return True

    def check_app_running(self):
        """检查应用是否在运行"""
        if SYSTEM_TYPE == 'Darwin':  # Mac系统
            return None  # Mac可以直接更新
            
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name']):
            try:
                if proc.info['pid'] == current_pid:
                    continue
                if proc.info['name'] == APP_NAME:
                    return proc.info['pid']
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return None

    def close_app(self, pid):
        """关闭应用"""
        try:
            process = psutil.Process(pid)
            process.terminate()
            try:
                process.wait(timeout=5)
            except psutil.TimeoutExpired:
                process.kill()
            return True
        except Exception as e:
            logging.error(f"关闭应用失败: {str(e)}")
            return False

    def download_update(self, version_info):
        """下载并应用更新"""
        try:
            latest_version = version_info['latest_version']
            version_data = version_info['versions'][latest_version]
            
            self.print_log(f"正在更新到版本 {latest_version}")
            self.print_log(f"更新说明: {version_data.get('description', '无')}")
            
            # 检查是否可以使用增量更新
            if 'patch' in version_data and version_data['patch']['from_version'] == self.current_version:
                self.print_log(f"使用增量更新从版本 {self.current_version} 更新到版本 {latest_version}")
                return self._incremental_update(version_info)
            else:
                self.print_log(f"使用完整更新从版本 {self.current_version} 更新到版本 {latest_version}")
                if 'patch' in version_data:
                    self.print_log(f"（完整更新原因：当前版本 {self.current_version} 无法使用增量更新到目标版本 {latest_version}）")
                else:
                    self.print_log("（完整更新原因：目标版本不支持增量更新）")
                return self._full_update(version_info)
            
        except Exception as e:
            logging.error(f"更新失败: {str(e)}")
            self.print_log(f"更新失败: {str(e)}")
            return False

    def _incremental_update(self, version_info):
        """增量更新"""
        try:
            latest_version = version_info['latest_version']
            version_data = version_info['versions'][latest_version]
            
            # 备份当前版本
            backup_path = self.backup_current_version()
            
            # 下载更新文件
            file_url = f"{self.server_url}/download/{latest_version}/{APP_NAME}"
            final_path = os.path.join(self.current_dir, APP_NAME)
            
            if not self.download_with_resume(file_url, final_path, f"下载 {APP_NAME}"):
                logging.error(f"下载文件失败")
                self.restore_from_backup(backup_path)
                return False
            
            # 验证MD5
            if self.get_file_md5(final_path) != version_data['md5']:
                logging.error("文件MD5校验失败")
                self.restore_from_backup(backup_path)
                return False
            
            # 更新版本信息
            self.current_version = latest_version
            self.save_current_version(latest_version)
            
            self.print_log("增量更新完成！")
            self.print_log("更新完成，建议重启应用以确保所有更改生效")
            return True
            
        except Exception as e:
            logging.error(f"增量更新失败: {str(e)}")
            self.print_log(f"增量更新失败: {str(e)}")
            return False

    def _full_update(self, version_info):
        """完整文件更新"""
        try:
            latest_version = version_info['latest_version']
            version_data = version_info['versions'][latest_version]
            
            self.print_log(f"正在更新到版本 {latest_version}")
            self.print_log(f"更新说明: {version_data.get('description', '无')}")
            self.print_log("使用完整更新")
            
            # 备份当前版本
            backup_path = self.backup_current_version()
            self.print_log(f"已备份当前版本到: {backup_path}")
            
            # 下载更新文件
            file_url = f"{self.server_url}/download/{latest_version}/{APP_NAME}"
            final_path = os.path.join(self.current_dir, APP_NAME)
            
            if not self.download_with_resume(file_url, final_path, f"下载 {APP_NAME}"):
                error_msg = "下载文件失败"
                logging.error(error_msg)
                self.print_log(f"更新失败: {error_msg}")
                self.print_log("正在回滚到备份版本...")
                self.restore_from_backup(backup_path)
                self.print_log("已恢复到之前版本")
                return False
            
            # 验证MD5
            expected_md5 = version_data['md5']
            actual_md5 = self.get_file_md5(final_path)
            self.print_log(f"期望的MD5值: {expected_md5}")
            self.print_log(f"实际的MD5值: {actual_md5}")
            
            if actual_md5 != expected_md5:
                error_msg = f"文件MD5校验失败，文件可能已损坏"
                logging.error(error_msg)
                self.print_log(f"更新失败: {error_msg}")
                self.print_log("正在回滚到备份版本...")
                self.restore_from_backup(backup_path)
                self.print_log("已恢复到之前版本")
                return False
            
            # 更新版本信息
            self.current_version = latest_version
            self.save_current_version(latest_version)
            
            self.print_log("更新成功！")
            self.print_log(f"已更新到版本: {latest_version}")
            return True
            
        except Exception as e:
            error_msg = f"更新过程出错: {str(e)}"
            logging.error(error_msg)
            self.print_log(f"更新失败: {error_msg}")
            if 'backup_path' in locals():
                self.print_log("正在回滚到备份版本...")
                self.restore_from_backup(backup_path)
                self.print_log("已恢复到之前版本")
            return False

    def print_log(self, message):
        """带时间戳的日志打印"""
        print(f"{self.log_time()} {message}")

if __name__ == "__main__":
    client = UpdateClient()
    update_info = client.check_for_updates()
    if update_info:
        client.download_update(update_info) 
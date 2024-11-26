import os
import json
import hashlib
import bsdiff4
import sys
import time
import threading
import multiprocessing
from tqdm import tqdm

# 添加父目录到系统路径以导入配置
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 获取配置文件路径
config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'server_config.json')

# 加载配置
with open(config_path, 'r') as f:
    config = json.load(f)
    SERVER_CONFIG = config['SERVER_CONFIG']
    APP_CONFIG = config['APP_CONFIG']

class ElapsedTimeThread(threading.Thread):
    """实时显示经过时间的线程"""
    def __init__(self):
        super().__init__()
        self.running = True
        self.start_time = time.time()
        self.daemon = True  # 设置为守护线程，主线程结束时会自动结束
    
    def run(self):
        while self.running:
            elapsed = time.time() - self.start_time
            print(f"\r正在计算差异文件，已用时: {elapsed:.1f} 秒", end="", flush=True)
            time.sleep(0.1)  # 每0.1秒更新一次
    
    def stop(self):
        self.running = False
        total_time = time.time() - self.start_time
        print(f"\r计算完成，总用时: {total_time:.1f} 秒")

class VersionManager:
    def __init__(self):
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_dir = os.path.join(self.base_dir, 'config')
        self.config_path = os.path.join(self.config_dir, 'versions.json')
        self.versions_dir = os.path.join(self.base_dir, 'versions')
        
        # 使用配置文件中的端口
        self.server_url = f"http://localhost:{SERVER_CONFIG['port']}"
        
        # 确保目录存在
        os.makedirs(self.config_dir, exist_ok=True)
        os.makedirs(self.versions_dir, exist_ok=True)
        
        # 如果配置文件不存在，创建初始配置
        if not os.path.exists(self.config_path):
            initial_config = {
                "latest_version": "1.0",
                "versions": {}
            }
            self.save_config(initial_config)

    def load_config(self):
        """加载版本配置"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {"latest_version": "1.0", "versions": {}}

    def save_config(self, config):
        """保存版本配置"""
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def calculate_md5(self, file_path):
        """计算文件MD5"""
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    def version_to_float(self, version):
        """将版本号转换为浮点数用于比较"""
        return float(version)

    def copy_with_progress(self, src_file, dest_file):
        """带进度显示的文件复制"""
        total_size = os.path.getsize(src_file)
        with open(src_file, 'rb') as fsrc:
            with open(dest_file, 'wb') as fdst:
                with tqdm(total=total_size, unit='B', unit_scale=True, desc="复制文件") as pbar:
                    while True:
                        buf = fsrc.read(8192)
                        if not buf:
                            break
                        fdst.write(buf)
                        pbar.update(len(buf))

    def add_version(self, version, file_path, description):
        """添加新版本"""
        try:
            config = self.load_config()
            
            # 创建版本目录
            version_dir = os.path.join(self.versions_dir, f'v{version}')
            os.makedirs(version_dir, exist_ok=True)
            
            # 复制可执行文件到版本目录（带进度显示）
            print(f"\n正在复制文件到版本目录...")
            dest_file = os.path.join(version_dir, 'app')
            self.copy_with_progress(file_path, dest_file)
            
            # 计算并显示文件大小
            file_size = os.path.getsize(dest_file)
            print(f"\n原文件大小: {file_size/1024/1024:.2f} MB")
            
            # 使用正确的版本号排序
            versions = sorted(
                [v for v in config['versions'].keys()],
                key=lambda x: tuple(map(int, x.split('.')))
            )
            
            if versions:
                prev_version = versions[-1]
                prev_file = os.path.join(self.versions_dir, f'v{prev_version}', 'app')
                
                if os.path.exists(prev_file):
                    print(f"\n正在生成与版本 {prev_version} 的差异文件...")
                    patch_file = os.path.join(self.base_dir, 'patches', f'patch_{prev_version}_to_{version}.diff')
                    os.makedirs(os.path.dirname(patch_file), exist_ok=True)
                    
                    # 启动计时器线程
                    timer = ElapsedTimeThread()
                    timer.start()
                    
                    try:
                        # 生成差异文件
                        bsdiff4.file_diff(prev_file, dest_file, patch_file)
                    finally:
                        # 停止计时器线程
                        timer.stop()
                        timer.join()
                    
                    # 计算差异文件的MD5
                    patch_md5 = self.calculate_md5(patch_file)
                    patch_size = os.path.getsize(patch_file)
                    
                    print(f"\n差异文件生成完成:")
                    print(f"差异文件大小: {patch_size/1024/1024:.2f} MB")
                    print(f"压缩比: {patch_size/file_size*100:.2f}%")
                    
                    config['versions'][version] = {
                        'files': ['app'],
                        'md5': self.calculate_md5(dest_file),
                        'description': description,
                        'patch': {
                            'from_version': prev_version,
                            'patch_file': os.path.basename(patch_file),
                            'md5': patch_md5
                        }
                    }
                else:
                    config['versions'][version] = {
                        'files': ['app'],
                        'md5': self.calculate_md5(dest_file),
                        'description': description
                    }
            else:
                config['versions'][version] = {
                    'files': ['app'],
                    'md5': self.calculate_md5(dest_file),
                    'description': description
                }
            
            # 更新最新版本号
            config['latest_version'] = version
            
            # 保存配置
            self.save_config(config)
            print(f"\n成功添加版本 {version}")
            
        except Exception as e:
            print(f"\n添加版本失败: {str(e)}")
            raise

    def cleanup_old_versions(self, max_versions=10):
        """清理旧版本信息"""
        try:
            config = self.load_config()
            versions = sorted(config['versions'].keys(), 
                            key=lambda x: tuple(map(int, x.split('.'))))
            
            # 如果版本数超过限制，删除旧版本
            if len(versions) > max_versions:
                for version in versions[:-max_versions]:
                    del config['versions'][version]
                
                # 保存更新后的配置
                self.save_config(config)
                print(f"已清理旧版本，保留最新的 {max_versions} 个版本")
        
        except Exception as e:
            print(f"清理旧版本失败: {str(e)}")

    def cleanup_old_patches(self, max_patches=10):
        """清理旧的差异文件，只保留最近的几个"""
        try:
            patches_dir = os.path.join(self.base_dir, 'patches')
            if not os.path.exists(patches_dir):
                return
            
            # 获取所有差异文件
            patches = []
            for item in os.listdir(patches_dir):
                if item.startswith('patch_') and item.endswith('.diff'):
                    patch_path = os.path.join(patches_dir, item)
                    # 获取文件修改时间作为排序依据
                    mtime = os.path.getmtime(patch_path)
                    patches.append((mtime, patch_path))
            
            # 按时间戳排序
            patches.sort(reverse=True)  # 最新的在前面
            
            # 如果差异文件数量超过限制，删除旧的文件
            if len(patches) > max_patches:
                for _, patch_path in patches[max_patches:]:
                    try:
                        os.remove(patch_path)
                        print(f"已删除旧的差异文件: {os.path.basename(patch_path)}")
                    except Exception as e:
                        print(f"删除差异文件失败 {os.path.basename(patch_path)}: {str(e)}")
                
                remaining = len(patches) - len(patches[max_patches:])
                print(f"已清理旧的差异文件，当前保留 {remaining} 个最新差异文件")
        
        except Exception as e:
            print(f"清理旧的差异文件失败: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="版本管理工具")
    parser.add_argument('--add', action='store_true', help="添加新版本")
    parser.add_argument('--version', type=str, help="版本号")
    parser.add_argument('--file', type=str, help="版本文件")
    parser.add_argument('--desc', type=str, help="版本描述")
    
    args = parser.parse_args()
    
    manager = VersionManager()
    
    if args.add:
        if not all([args.version, args.file, args.desc]):
            print("添加版本需要提供: --version <版本号> --file <版本文件> --desc <版本描述>")
        else:
            manager.add_version(args.version, args.file, args.desc)
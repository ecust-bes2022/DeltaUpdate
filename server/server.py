from fastapi import FastAPI, HTTPException, Response, Header
from fastapi.responses import FileResponse, HTMLResponse
from contextlib import asynccontextmanager
from typing import Optional
import os
import json
import hashlib
import logging
from datetime import datetime

# 获取服务器脚本所在的目录路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 加载配置
with open(os.path.join(BASE_DIR, 'server_config.json'), 'r') as f:
    config = json.load(f)
    SERVER_CONFIG = config['SERVER_CONFIG']
    APP_CONFIG = config['APP_CONFIG']
    DIR_CONFIG = config['DIR_CONFIG']

# 设置目录路径
VERSIONS_DIR = os.path.join(BASE_DIR, DIR_CONFIG['versions_dir'])
PATCHES_DIR = os.path.join(BASE_DIR, DIR_CONFIG['patches_dir'])
LOG_DIR = os.path.join(BASE_DIR, DIR_CONFIG['logs_dir'])
LOG_LEVEL = DIR_CONFIG['log_level']

# 配置日志
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    filename=os.path.join(LOG_DIR, 'server.log'),
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(levelname)s - %(message)s'
)

app = FastAPI(title="软件增量更新系统")

def load_version_info():
    """加载版本配置"""
    config_path = os.path.join(BASE_DIR, 'config', 'versions.json')
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)

VERSION_INFO = load_version_info()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务器生命周期管理"""
    # 启动时的操作
    global VERSION_INFO
    
    # 确保必要的目录存在
    os.makedirs(VERSIONS_DIR, exist_ok=True)
    os.makedirs(PATCHES_DIR, exist_ok=True)
    
    # 确保版本目录存在并创建测试文件
    for version, info in VERSION_INFO['versions'].items():
        version_dir = os.path.join(VERSIONS_DIR, f'v{version}')
        os.makedirs(version_dir, exist_ok=True)
        
        file_path = os.path.join(version_dir, 'app.txt')
        if os.path.exists(file_path):
            # 如果文件已存在，只更新MD5
            info['md5'] = calculate_file_md5(file_path)
            logging.info(f"更新版本 {version} 的文件 MD5: {info['md5']}")
    
    yield
    
    # 关闭时的操作
    pass

def calculate_file_md5(file_path):
    """计算文件MD5"""
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()

@app.get("/check_update")
async def check_update():
    """检查更新接口"""
    return VERSION_INFO

@app.get("/download/{version}/{filename}")
async def download_file(
    version: str, 
    filename: str, 
    range: Optional[str] = Header(default=None)
):
    """文件下载接口"""
    file_path = os.path.join(VERSIONS_DIR, f'v{version}', filename)
    if not os.path.exists(file_path):
        logging.error(f"文件未找到: {file_path}")
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, filename=filename)

@app.get("/download_patch/{from_version}/{to_version}")
async def download_patch(from_version: str, to_version: str):
    """下载差异文件"""
    patch_file = os.path.join(PATCHES_DIR, f'patch_{from_version}_to_{to_version}.diff')
    if not os.path.exists(patch_file):
        raise HTTPException(status_code=404, detail="Patch file not found")
    return FileResponse(patch_file)

@app.get("/", response_class=HTMLResponse)
async def root():
    """根路径处理"""
    return """
    <html>
        <head>
            <title>软件增量更新系统</title>
        </head>
        <body>
            <h1>软件增量更新系统</h1>
            <p>可用的API端点：</p>
            <ul>
                <li><a href="/docs">/docs</a> - API文档</li>
                <li><a href="/check_update">/check_update</a> - 检查更新</li>
                <li>/download/{version}/{filename} - 下载文件</li>
                <li>/download_patch/{from_version}/{to_version} - 下载差异文件</li>
            </ul>
        </body>
    </html>
    """

@app.get("/reload_config")
async def reload_config():
    """重新加载配置接口"""
    global VERSION_INFO
    try:
        VERSION_INFO = load_version_info()
        logging.info("配置重新加载成功")
        return {"status": "success", "message": "配置已重新加载"}
    except Exception as e:
        logging.error(f"重新加载配置失败: {str(e)}")
        raise HTTPException(status_code=500, detail="重新加载配置失败")

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        app, 
        host=SERVER_CONFIG['host'], 
        port=SERVER_CONFIG['port']
    )
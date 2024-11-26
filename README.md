# 软件增量更新系统

## 项目简介
该项目实现了一个基于Python的软件增量更新系统，支持客户端软件的版本检查和自动更新。系统采用增量更新方式，仅传输文件的变化部分，大大减少更新时的数据传输量。

## 技术栈
- **后端框架**: FastAPI 0.110.0
- **ASGI服务器**: Uvicorn 0.27.1
- **增量更新**: bsdiff4 1.2.4
- **网络请求**: requests 2.31.0
- **进度显示**: tqdm 4.66.1
- **GUI框架**: PySide6 6.5.2

## 系统架构
```
project/
├── server/                     # 服务器端
│   ├── versions/              # 存放不同版本的完整文件
│   ├── patches/              # 存放版本间的差异文件
│   ├── tools/                # 工具目录
│   │   └── version_manager.py # 版本管理工具
│   ├── server_config.json    # 服务器配置文件
│   ├── server.py            # 服务器主程序
│   └── run_server.py        # 服务器启动脚本
├── client/                    # 客户端
│   ├── current_version/      # 当前版本文件
│   │   └── version.json     # 版本信息记录
│   ├── backup/              # 更新前的备份
│   ├── temp/                # 临时文件目录
│   ├── client_config.json   # 客户端配置
│   ├── client.py            # 客户端主程序
│   └── run_client.py        # 客户端启动脚本
├── update_manager.py         # 更新管理器
└── main.py                   # 主程序入口
```

## 配置说明
### 服务器配置 (server_config.json)
```json
{
    "SERVER_CONFIG": {
        "host": "0.0.0.0",
        "port": 1218,
        "debug": false
    },
    "APP_CONFIG": {
        "version": "20.0",
        "app_path": "/path/to/app",
        "description": "新版本说明"
    },
    "DIR_CONFIG": {
        "versions_dir": "versions",
        "patches_dir": "patches",
        "logs_dir": "logs",
        "log_level": "INFO"
    }
}
```

### 客户端配置 (client_config.json)
```json
{
    "SERVER": {
        "URL": "http://127.0.0.1",
        "PORT": 1218
    },
    "APP_NAME": "app"
}
```

## 部署说明
### 服务器端
1. 配置服务器：
   - 修改 server_config.json 中的配置
   - 确保必要的目录存在

2. 启动服务器：
```bash
python server/run_server.py
```

### 客户端
1. 配置客户端：
   - 修改 client_config.json 中的服务器地址

2. 运行客户端：
```bash
python main.py
```

## 版本管理
### 添加新版本
1. 修改服务器配置：
   - 在 server_config.json 中更新版本信息

2. 生成新版本：
```bash
python server/generate_version.py
```

### 更新特性
- 支持增量更新和完整更新
- 自动选择最优更新方式
- 更新过程显示详细进度
- 支持更新失败回滚
- 保留最近10个版本备份
- 保留最近10个差异文件
- 自动清理旧的备份和差异文件
- 支持断点续传功能
  - 支持大文件下载
  - 网络中断后可继续下载
  - 实时显示下载进度
  - 临时文件自动处理

### 注意事项
1. 版本号使用数字格式（如：1.0、2.0、11.0）
2. 版本信息保存在 server/config/versions.json 中
3. 版本文件保存在 server/versions/v{version} 目录下
4. 确保服务器端口（默认1218）已在防火墙中开放

## 更新日志
### 2024-11-02
- [x] 配置文件改进
  - 将配置文件改为JSON格式
  - 分离服务器和客户端配置
  - 优化配置结构
- [x] 系统类型检测优化
  - 移除配置中的系统类型
  - 改用动态检测系统类型
- [x] 更新流程优化
  - 改进增量更新判断逻辑
  - 添加更详细的更新信息提示
  - 优化版本比较机制
- [x] 文件管理优化
  - 自动清理旧备份
  - 自动清理旧差异文件
  - 限制保留版本数量

[之前的更新记录...]

## 待实现功能
- [ ] 支持多文件同时更新
- [ ] 添加更新任务队列
- [ ] 实现更新通知机制
- [ ] 支持配置文件更新
- [ ] 添加更新日志记录
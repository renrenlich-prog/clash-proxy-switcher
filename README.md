# 代理切换器

一键切换 Windows 系统代理的轻量桌面工具。专为 Clash VPN 用户设计，手机端开启代理后，电脑端点击按钮即可切换网络代理状态。

## 功能

- **一键切换** — 点击按钮开启/关闭 Windows 系统代理，无需进入系统设置
- **多配置管理** — 支持保存多个代理配置（家里、公司等），下拉切换，即时生效
- **启动自动连接** — 打开软件后自动连接上次使用的代理
- **系统托盘** — 关闭窗口后最小化到系统托盘，右键可恢复或退出
- **配置文件持久化** — 所有配置保存在本地 JSON，下次启动自动加载

## 使用方法

### 直接运行（需要 Python 3.11+）

```bash
pip install -r requirements.txt
python main.py
```

### 运行打包好的 exe

下载 [Releases](https://github.com/renrenlich-prog/clash-proxy-switcher/releases) 中的 `ProxySwitcher.exe`，双击运行。

首次运行会自动生成 `config.json`，默认包含"家里"配置（IP: 192.168.31.104, 端口: 6666）。

## 界面预览

- 淡蓝色主色调
- 状态灯：绿色 = 代理已连接，灰色 = 代理已断开
- 下拉框切换配置，设置窗口管理配置列表

## 开发

```bash
# 安装依赖
pip install -r requirements.txt

# 打包为 exe
pyinstaller --onefile --windowed --icon=cat.ico --add-data "cat.ico;." --name "ProxySwitcher" main.py
```

打包产物在 `dist/ProxySwitcher.exe`。

## 技术栈

- Python 3.11 + tkinter
- pystray（系统托盘）
- Pillow（图标处理）
- PyInstaller（打包）
- 通过 Windows 注册表控制代理（`winreg`）

## 项目结构

```
├── main.py            # 主程序 GUI
├── proxy_core.py      # 注册表操作核心
├── data_manager.py    # 配置数据管理
├── cat.ico            # 应用图标
├── cat.png            # 原始图标素材
└── requirements.txt   # Python 依赖
```

## License

MIT

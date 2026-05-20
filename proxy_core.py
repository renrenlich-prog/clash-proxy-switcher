"""代理核心模块 —— 操作 Windows 注册表控制系统代理开关。

通过 winreg 直接读写注册表，无须调用系统设置窗口。
修改后通过 InternetSetOptionW 通知系统立即生效。
"""

import winreg
import ctypes


REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"


def _notify_system():
    """通知 Windows 代理设置已变更，使修改立即生效。"""
    INTERNET_OPTION_SETTINGS_CHANGED = 39
    INTERNET_OPTION_REFRESH = 37

    wininet = ctypes.windll.wininet

    wininet.InternetSetOptionW(0, INTERNET_OPTION_REFRESH, 0, 0)
    wininet.InternetSetOptionW(0, INTERNET_OPTION_SETTINGS_CHANGED, 0, 0)


def enable_proxy(ip: str, port: int):
    """开启代理并设置 IP 和端口。"""
    server = f"{ip}:{port}"

    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, server)
    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
    winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, "<local>")
    winreg.CloseKey(key)

    _notify_system()


def disable_proxy():
    """关闭代理，保留代理地址配置不变以便下次快速开启。"""
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_SET_VALUE
    )
    winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
    winreg.CloseKey(key)

    _notify_system()


def get_status() -> dict:
    """返回当前代理状态。

    Returns:
        {"enabled": bool, "server": "ip:port" | None}
    """
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_READ
    )

    try:
        enabled_val, _ = winreg.QueryValueEx(key, "ProxyEnable")
        enabled = bool(enabled_val)
    except FileNotFoundError:
        enabled = False

    try:
        server, _ = winreg.QueryValueEx(key, "ProxyServer")
    except FileNotFoundError:
        server = None

    winreg.CloseKey(key)

    return {"enabled": enabled, "server": server}


if __name__ == "__main__":
    # 简单的命令行测试
    import sys

    if len(sys.argv) == 3:
        _, ip, port = sys.argv
        print(f"开启代理 {ip}:{port}")
        enable_proxy(ip, int(port))
    elif len(sys.argv) == 2 and sys.argv[1] == "off":
        print("关闭代理")
        disable_proxy()
    else:
        status = get_status()
        print(f"代理状态: {'开启' if status['enabled'] else '关闭'}")
        if status["server"]:
            print(f"代理地址: {status['server']}")

    status = get_status()
    print(f"当前状态: {status}")

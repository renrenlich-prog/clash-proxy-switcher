"""配置数据管理层 —— 多代理配置的 JSON 持久化储存。

配置文件位于 config.json，包含：
- 多个代理配置（名称、IP、端口）
- 上次使用的配置名称
- 是否启动时自动连接
"""
import json
import os
import sys

if getattr(sys, 'frozen', False):
    # 打包后 exe 同目录下
    CONFIG_PATH = os.path.join(os.path.dirname(sys.executable), "config.json")
else:
    CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

_DEFAULT_CONFIG = {
    "profiles": [
        {"name": "家里", "ip": "192.168.31.104", "port": 6666}
    ],
    "last_used": "家里",
    "auto_connect": True,
}


class ConfigManager:
    """管理代理配置文件（单例）。"""

    def __init__(self):
        self._ensure_config_exists()

    def _ensure_config_exists(self):
        """配置文件不存在时创建默认配置。"""
        if not os.path.exists(CONFIG_PATH):
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(_DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)

    def _read(self) -> dict:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)

    def _write(self, data: dict):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ---- 配置列表 ----

    def get_all_profiles(self) -> list[dict]:
        """返回所有代理配置列表。"""
        return self._read()["profiles"]

    def get_profile(self, name: str) -> dict | None:
        """按名称查找配置，不存在返回 None。"""
        for p in self._read()["profiles"]:
            if p["name"] == name:
                return p
        return None

    def add_profile(self, name: str, ip: str, port: int):
        """添加新配置。重名时抛出 ValueError。"""
        data = self._read()
        if any(p["name"] == name for p in data["profiles"]):
            raise ValueError(f"配置名称 '{name}' 已存在")
        data["profiles"].append({"name": name, "ip": ip, "port": port})
        self._write(data)

    def remove_profile(self, name: str):
        """删除配置。并清理 last_used 引用。"""
        data = self._read()
        data["profiles"] = [p for p in data["profiles"] if p["name"] != name]
        if data["last_used"] == name:
            data["last_used"] = data["profiles"][0]["name"] if data["profiles"] else ""
        self._write(data)

    def update_profile(self, old_name: str, new_name: str, ip: str, port: int):
        """更新已有配置。改名为已有名称时抛出 ValueError。"""
        data = self._read()
        for p in data["profiles"]:
            if p["name"] == old_name:
                if new_name != old_name and any(q["name"] == new_name for q in data["profiles"]):
                    raise ValueError(f"配置名称 '{new_name}' 已存在")
                p["name"] = new_name
                p["ip"] = ip
                p["port"] = port
                break
        if data["last_used"] == old_name:
            data["last_used"] = new_name
        self._write(data)

    # ---- 上次使用 / 自动连接 ----

    def get_last_used(self) -> dict | None:
        """返回上次使用的配置，不存在则返回 None。"""
        data = self._read()
        return self.get_profile(data["last_used"])

    def set_last_used(self, name: str):
        data = self._read()
        data["last_used"] = name
        self._write(data)

    def get_auto_connect(self) -> bool:
        return self._read()["auto_connect"]

    def set_auto_connect(self, enabled: bool):
        data = self._read()
        data["auto_connect"] = enabled
        self._write(data)

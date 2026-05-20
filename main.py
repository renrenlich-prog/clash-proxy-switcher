"""代理切换器 —— 一个轻量的 Windows 系统代理一键切换工具。"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox

import pystray
from PIL import Image

from proxy_core import enable_proxy, disable_proxy, get_status
from data_manager import ConfigManager

if getattr(sys, 'frozen', False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ICO_PATH = os.path.join(BASE_DIR, "cat.ico")


# ---- 配色方案（淡蓝主题） ----
BG_COLOR = "#e8f4fd"          # 窗口背景
ACCENT = "#3498db"            # 强调蓝
BUTTON_COLOR = "#5b9bd5"      # 按钮蓝
TEXT_COLOR = "#2c3e50"        # 文字深灰蓝
ON_COLOR = "#2ecc71"          # 连接状态绿
OFF_COLOR = "#bdc3c7"         # 断开状态灰
HINT_COLOR = "#7f8c8d"        # 提示文字灰

WINDOW_WIDTH = 360
WINDOW_HEIGHT = 300
STATUS_RADIUS = 18


class ProxySwitcher:
    def __init__(self):
        self.config = ConfigManager()
        self._tray_icon = None
        self._quitting = False

        # ---- 主窗口 ----
        self.root = tk.Tk()
        self.root.title("代理切换器")
        self.root.iconbitmap(ICO_PATH)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.resizable(False, False)
        self.root.configure(bg=BG_COLOR)
        self._center_window(self.root, WINDOW_WIDTH, WINDOW_HEIGHT)

        # 关闭按钮 → 最小化到托盘
        self.root.protocol("WM_DELETE_WINDOW", self._hide_window)

        # ---- 样式 ----
        self._setup_style()

        # ---- 界面组件 ----
        self._build_ui()

        # ---- 系统托盘 ----
        self._setup_tray()

        # ---- 启动时自动连接 ----
        self.root.after(200, self._auto_connect_on_start)

    # ==================== 工具方法 ====================

    @staticmethod
    def _center_window(win, w, h):
        """将窗口居中显示。"""
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        win.geometry(f"+{x}+{y}")

    # ==================== 样式设置 ====================

    def _setup_style(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure(
            "Profile.TCombobox",
            fieldbackground="white",
            background="white",
            foreground=TEXT_COLOR,
            arrowcolor=ACCENT,
            selectbackground=ACCENT,
            selectforeground="white",
        )

    # ==================== UI 构建 ====================

    def _build_ui(self):
        # 标题
        tk.Label(
            self.root, text="网络代理即时切换",
            font=("Microsoft YaHei", 14, "bold"),
            fg=TEXT_COLOR, bg=BG_COLOR,
        ).pack(pady=(24, 6))

        # 状态灯
        self.canvas = tk.Canvas(
            self.root, width=STATUS_RADIUS * 2, height=STATUS_RADIUS * 2,
            bg=BG_COLOR, highlightthickness=0,
        )
        self.canvas.pack(pady=(8, 0))
        self.status_circle = self.canvas.create_oval(
            2, 2, STATUS_RADIUS * 2 - 2, STATUS_RADIUS * 2 - 2,
            fill=OFF_COLOR, outline="",
        )

        # 状态文字
        self.status_label = tk.Label(
            self.root, text="代理已关闭",
            font=("Microsoft YaHei", 11),
            fg=TEXT_COLOR, bg=BG_COLOR,
        )
        self.status_label.pack(pady=(4, 4))

        # 配置选择下拉框
        self._build_profile_selector()

        # 核心切换按钮
        self.toggle_btn = tk.Button(
            self.root, text="开启代理",
            font=("Microsoft YaHei", 12, "bold"),
            bg=BUTTON_COLOR, fg="white",
            activebackground=ACCENT, activeforeground="white",
            border=0, padx=40, pady=10,
            cursor="hand2",
            command=self._on_toggle,
        )
        self.toggle_btn.pack(pady=(0, 10))

        # 底部设置按钮
        tk.Button(
            self.root, text="管理配置",
            font=("Microsoft YaHei", 9),
            bg=BG_COLOR, fg=ACCENT,
            border=0, cursor="hand2",
            command=self._open_settings,
        ).pack()

    def _build_profile_selector(self):
        """配置选择行：标签 + 下拉框。"""
        frame = tk.Frame(self.root, bg=BG_COLOR)
        frame.pack(pady=(0, 16))

        tk.Label(
            frame, text="配置：",
            font=("Microsoft YaHei", 9),
            fg=HINT_COLOR, bg=BG_COLOR,
        ).pack(side=tk.LEFT, padx=(0, 6))

        profiles = [p["name"] for p in self.config.get_all_profiles()]
        self.profile_var = tk.StringVar()
        self.profile_combo = ttk.Combobox(
            frame, textvariable=self.profile_var,
            values=profiles, state="readonly",
            width=18,
        )
        self.profile_combo.pack(side=tk.LEFT)
        self.profile_combo.bind("<<ComboboxSelected>>", self._on_profile_changed)

        # 默认选中上次使用的配置
        last = self.config.get_last_used()
        if last:
            self.profile_var.set(last["name"])

    # ==================== 状态刷新 ====================

    def _refresh(self):
        """根据当前代理状态更新界面。"""
        status = get_status()
        profile = self.config.get_last_used()
        expected_server = f"{profile['ip']}:{profile['port']}" if profile else ""

        is_on = status["enabled"] and status["server"] == expected_server

        if is_on:
            self.canvas.itemconfig(self.status_circle, fill=ON_COLOR)
            self.status_label.config(text="代理已开启")
            self.toggle_btn.config(text="关闭代理", bg="#e74c3c")
        else:
            self.canvas.itemconfig(self.status_circle, fill=OFF_COLOR)
            self.status_label.config(text="代理已关闭")
            self.toggle_btn.config(text="开启代理", bg=BUTTON_COLOR)

    def _refresh_combo(self):
        """刷新下拉框中的配置列表。"""
        profiles = [p["name"] for p in self.config.get_all_profiles()]
        self.profile_combo["values"] = profiles
        last = self.config.get_last_used()
        if last:
            self.profile_var.set(last["name"])

    # ==================== 事件处理 ====================

    def _auto_connect_on_start(self):
        if not self.config.get_auto_connect():
            self._refresh()
            return
        profile = self.config.get_last_used()
        if profile:
            enable_proxy(profile["ip"], profile["port"])
        self._refresh()

    def _on_toggle(self):
        status = get_status()
        if status["enabled"]:
            disable_proxy()
        else:
            profile = self.config.get_last_used()
            if not profile:
                self.status_label.config(text="请先选择一个配置")
                return
            enable_proxy(profile["ip"], profile["port"])
        self._refresh()

    def _on_profile_changed(self, event=None):
        """下拉框切换配置时触发。"""
        name = self.profile_var.get()
        profile = self.config.get_profile(name)
        if not profile:
            return

        self.config.set_last_used(name)

        # 如果当前代理开着，立即切换到新配置
        status = get_status()
        if status["enabled"]:
            enable_proxy(profile["ip"], profile["port"])

        self._refresh()

    # ==================== 系统托盘 ====================

    def _setup_tray(self):
        """在独立线程中启动系统托盘图标。"""
        tray_img = Image.open(ICO_PATH)
        self._tray_icon = pystray.Icon(
            "proxy_switcher", tray_img,
            menu=pystray.Menu(
                pystray.MenuItem("显示窗口", self._show_window, default=True),
                pystray.MenuItem("退出", self._quit_app),
            ),
        )

    def _show_window(self):
        """从托盘恢复窗口。"""
        self.root.after(0, self.root.deiconify)

    def _hide_window(self):
        """最小化到系统托盘。"""
        self.root.withdraw()
        if not hasattr(self, "_tray_shown"):
            self._tray_shown = True
            # 首次最小化时提示
            self._tray_icon.notify("代理切换器已最小化到系统托盘", "代理切换器")

    def _quit_app(self):
        """彻底退出。"""
        self._quitting = True
        self._tray_icon.stop()
        self.root.after(0, self.root.destroy)

    # ==================== 配置管理窗口 ====================

    def _open_settings(self):
        """打开配置管理对话框。"""
        dialog = SettingsDialog(self.root, self.config, self._refresh_all)
        self.root.wait_window(dialog.window)
        self._refresh_all()

    def _refresh_all(self):
        self._refresh_combo()
        self._refresh()

    def run(self):
        self._refresh()

        # 在独立线程中运行托盘图标
        if self._tray_icon:
            threading.Thread(target=self._tray_icon.run, daemon=True).start()

        self.root.mainloop()


# ==================== 配置管理对话框 ====================

SETTINGS_WIDTH = 420
SETTINGS_HEIGHT = 420


class SettingsDialog:
    def __init__(self, parent, config: ConfigManager, on_close):
        self.config = config
        self.on_close = on_close
        self.selected_name = None

        self.window = tk.Toplevel(parent)
        self.window.title("管理代理配置")
        self.window.geometry(f"{SETTINGS_WIDTH}x{SETTINGS_HEIGHT}")
        self.window.resizable(False, False)
        self.window.configure(bg=BG_COLOR)
        self._center_window(self.window, SETTINGS_WIDTH, SETTINGS_HEIGHT)
        self.window.transient(parent)
        self.window.grab_set()

        self._build_ui()
        self._refresh_list()

    def _center_window(self, win, w, h):
        win.update_idletasks()
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        win.geometry(f"+{x}+{y}")

    # ==================== UI 构建 ====================

    def _build_ui(self):
        # ---- 配置列表 ----
        list_frame = tk.LabelFrame(
            self.window, text="已保存的配置",
            font=("Microsoft YaHei", 9),
            fg=TEXT_COLOR, bg=BG_COLOR,
        )
        list_frame.pack(fill=tk.BOTH, expand=True, padx=16, pady=(16, 8))

        self.listbox = tk.Listbox(
            list_frame,
            font=("Consolas", 10),
            bg="white", fg=TEXT_COLOR, selectbackground=ACCENT,
            selectforeground="white", border=0,
            activestyle="none",
        )
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        # ---- 编辑区域 ----
        entry_frame = tk.Frame(self.window, bg=BG_COLOR)
        entry_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        # 行1：名称
        tk.Label(entry_frame, text="名称", font=("Microsoft YaHei", 9),
                 fg=TEXT_COLOR, bg=BG_COLOR).grid(row=0, column=0, sticky="e", pady=3)
        self.name_entry = tk.Entry(entry_frame, font=("Microsoft YaHei", 10),
                                   width=14)
        self.name_entry.grid(row=0, column=1, padx=(6, 16), pady=3)

        # 行1：IP
        tk.Label(entry_frame, text="IP", font=("Microsoft YaHei", 9),
                 fg=TEXT_COLOR, bg=BG_COLOR).grid(row=0, column=2, sticky="e", pady=3)
        self.ip_entry = tk.Entry(entry_frame, font=("Microsoft YaHei", 10),
                                 width=14)
        self.ip_entry.grid(row=0, column=3, padx=(6, 0), pady=3)

        # 行2：端口
        tk.Label(entry_frame, text="端口", font=("Microsoft YaHei", 9),
                 fg=TEXT_COLOR, bg=BG_COLOR).grid(row=1, column=0, sticky="e", pady=3)
        self.port_entry = tk.Entry(entry_frame, font=("Microsoft YaHei", 10),
                                   width=14)
        self.port_entry.grid(row=1, column=1, padx=(6, 16), pady=3)

        # ---- 操作按钮行 ----
        btn_frame = tk.Frame(self.window, bg=BG_COLOR)
        btn_frame.pack(fill=tk.X, padx=16, pady=(0, 8))

        self._make_btn(btn_frame, "新增", self._on_add).pack(side=tk.LEFT, padx=(0, 8))
        self._make_btn(btn_frame, "保存修改", self._on_update).pack(side=tk.LEFT, padx=(0, 8))
        self._make_btn(btn_frame, "删除", self._on_delete).pack(side=tk.LEFT)

        # ---- 自动连接复选框 ----
        self.auto_var = tk.BooleanVar(value=self.config.get_auto_connect())
        tk.Checkbutton(
            self.window, text="启动软件时自动连接代理",
            variable=self.auto_var,
            font=("Microsoft YaHei", 9),
            fg=TEXT_COLOR, bg=BG_COLOR,
            activebackground=BG_COLOR,
            selectcolor=BG_COLOR,
            command=self._on_auto_changed,
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # ---- 关闭按钮 ----
        tk.Button(
            self.window, text="关闭",
            font=("Microsoft YaHei", 10),
            bg=BUTTON_COLOR, fg="white",
            activebackground=ACCENT, activeforeground="white",
            border=0, padx=24, pady=6,
            cursor="hand2",
            command=self.window.destroy,
        ).pack(pady=(0, 12))

    def _make_btn(self, parent, text, command):
        return tk.Button(
            parent, text=text,
            font=("Microsoft YaHei", 9),
            bg=ACCENT, fg="white",
            activebackground=BUTTON_COLOR, activeforeground="white",
            border=0, padx=10, pady=4,
            cursor="hand2",
            command=command,
        )

    # ==================== 列表操作 ====================

    def _refresh_list(self):
        self.listbox.delete(0, tk.END)
        for p in self.config.get_all_profiles():
            self.listbox.insert(tk.END, f"  {p['name']:<12}  {p['ip']}:{p['port']}")

    def _on_select(self, event=None):
        sel = self.listbox.curselection()
        if not sel:
            return
        profile = self.config.get_all_profiles()[sel[0]]
        self.selected_name = profile["name"]
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, profile["name"])
        self.ip_entry.delete(0, tk.END)
        self.ip_entry.insert(0, profile["ip"])
        self.port_entry.delete(0, tk.END)
        self.port_entry.insert(0, str(profile["port"]))

    # ==================== 按钮事件 ====================

    def _on_add(self):
        name = self.name_entry.get().strip()
        ip = self.ip_entry.get().strip()
        port_str = self.port_entry.get().strip()

        if not name or not ip or not port_str:
            messagebox.showwarning("提示", "名称、IP 和端口不能为空", parent=self.window)
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showwarning("提示", "端口必须是一个数字", parent=self.window)
            return

        try:
            self.config.add_profile(name, ip, port)
        except ValueError as e:
            messagebox.showwarning("提示", str(e), parent=self.window)
            return

        self._clear_entries()
        self._refresh_list()

    def _on_update(self):
        if not self.selected_name:
            messagebox.showwarning("提示", "请先在列表中选中要修改的配置", parent=self.window)
            return

        new_name = self.name_entry.get().strip()
        ip = self.ip_entry.get().strip()
        port_str = self.port_entry.get().strip()

        if not new_name or not ip or not port_str:
            messagebox.showwarning("提示", "名称、IP 和端口不能为空", parent=self.window)
            return
        try:
            port = int(port_str)
        except ValueError:
            messagebox.showwarning("提示", "端口必须是一个数字", parent=self.window)
            return

        try:
            self.config.update_profile(self.selected_name, new_name, ip, port)
        except ValueError as e:
            messagebox.showwarning("提示", str(e), parent=self.window)
            return

        self.selected_name = new_name
        self._refresh_list()

    def _on_delete(self):
        if not self.selected_name:
            messagebox.showwarning("提示", "请先在列表中选中要删除的配置", parent=self.window)
            return

        profiles = self.config.get_all_profiles()
        if len(profiles) <= 1:
            messagebox.showwarning("提示", "至少保留一个配置", parent=self.window)
            return

        self.config.remove_profile(self.selected_name)
        self.selected_name = None
        self._clear_entries()
        self._refresh_list()

    def _on_auto_changed(self):
        self.config.set_auto_connect(self.auto_var.get())

    def _clear_entries(self):
        self.name_entry.delete(0, tk.END)
        self.ip_entry.delete(0, tk.END)
        self.port_entry.delete(0, tk.END)


# ==================== 启动 ====================

if __name__ == "__main__":
    app = ProxySwitcher()
    app.run()

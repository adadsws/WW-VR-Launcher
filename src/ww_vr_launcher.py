"""
ww_vr_launcher.py  -  Wuthering Waves VR Launcher (UEVR Injector)
Enables VR mode for Wuthering Waves via the UEVR framework.

Requirements: Python 3.9+, Windows 10/11, customtkinter
Usage:  python ww_vr_launcher.py
"""
from __future__ import annotations

import sys
import os
import threading
import time
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

# Local modules
from injector import DLLInjector, GAME_EXE, is_admin
from config_manager import ConfigManager

VERSION = "1.0.0"

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class App(ctk.CTk):

    def __init__(self) -> None:
        super().__init__()

        self.title(f"鸣潮 VR 启动器  ·  Wuthering Waves VR Launcher  v{VERSION}")
        self.geometry("920x720")
        self.minsize(760, 600)

        self.cfg      = ConfigManager()
        self.injector = DLLInjector(log_callback=self._log)

        self.game_pid:          int | None = None
        self._monitoring:       bool       = False
        self._already_injected: bool       = False

        self.cfg.load_all()

        # DLLs are bundled in the project's dlls/ folder
        self.cfg.uevr_folder = os.path.normpath(
            os.path.join(os.path.dirname(__file__), "..", "dlls")
        )

        self._sliders: list = []  # (CTkSlider, default_value) for reset
        self._build_ui()
        self._update_ui_from_config()
        self._start_monitor()

        self._log(f"[LOG] WW VR Launcher v{VERSION} started")
        self._log(f"[LOG] Profile: {self.cfg.profile_path}")
        self._log(f"[LOG] Target:  {GAME_EXE}")
        if not is_admin():
            self._log("[WARN] Not running as Administrator — injection may fail if game is elevated.")

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # ── Top bar ────────────────────────────────────────────────────────────
        topbar = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "gray17"))
        topbar.pack(fill=tk.X)

        ctk.CTkLabel(topbar, text="⚡ 鸣潮 VR LAUNCHER",
                     font=ctk.CTkFont(size=14, weight="bold")).pack(side=tk.LEFT, padx=14, pady=8)

        # Injection status (rightmost)
        self._inject_dot   = ctk.CTkLabel(topbar, text="●", text_color="gray",
                                           font=ctk.CTkFont(size=16))
        self._inject_label = ctk.CTkLabel(topbar, text="未注入  Not Injected",
                                           font=ctk.CTkFont(size=11))
        self._inject_dot.pack(side=tk.RIGHT, padx=(0, 14), pady=8)
        self._inject_label.pack(side=tk.RIGHT, padx=4)

        # Separator
        ctk.CTkLabel(topbar, text="│", text_color="gray",
                     font=ctk.CTkFont(size=14)).pack(side=tk.RIGHT, padx=6)

        # Game status
        self._status_dot   = ctk.CTkLabel(topbar, text="●", text_color="red",
                                           font=ctk.CTkFont(size=16))
        self._status_label = ctk.CTkLabel(topbar, text="游戏未运行  Game Not Running",
                                           font=ctk.CTkFont(size=11))
        self._status_dot.pack(side=tk.RIGHT, padx=(0, 4), pady=8)
        self._status_label.pack(side=tk.RIGHT, padx=4)

        # ── Content wrapper ────────────────────────────────────────────────────
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill=tk.BOTH, expand=True, padx=12, pady=8)


        # ── Action row ─────────────────────────────────────────────────────────
        action = ctk.CTkFrame(content, fg_color="transparent")
        action.pack(fill=tk.X, pady=(0, 6))

        self._inject_btn = ctk.CTkButton(
            action, text="💉  注入 VR  Inject VR",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=190, height=40,
            command=self._do_inject
        )
        self._inject_btn.pack(side=tk.LEFT, padx=(0, 12))

        self._auto_inject_var = tk.BooleanVar()
        self._auto_focus_var  = tk.BooleanVar()
        self._auto_close_var  = tk.BooleanVar()

        opts = ctk.CTkFrame(action, fg_color="transparent")
        opts.pack(side=tk.LEFT)

        ctk.CTkCheckBox(opts, text="自动注入  Auto-Inject",
                         variable=self._auto_inject_var,
                         command=self._on_action_opts_changed).pack(side=tk.LEFT, padx=6)

        ctk.CTkLabel(opts, text="延迟  Delay:",
                     font=ctk.CTkFont(size=11)).pack(side=tk.LEFT, padx=(8, 2))
        self._delay_var = tk.StringVar(value="1")
        ctk.CTkEntry(opts, textvariable=self._delay_var, width=46,
                      justify="center").pack(side=tk.LEFT)
        ctk.CTkLabel(opts, text="s",
                     font=ctk.CTkFont(size=11)).pack(side=tk.LEFT, padx=(2, 8))

        ctk.CTkCheckBox(opts, text="聚焦游戏  Focus Game",
                         variable=self._auto_focus_var,
                         command=self._on_action_opts_changed).pack(side=tk.LEFT, padx=6)
        ctk.CTkCheckBox(opts, text="注后关闭  Auto-Close",
                         variable=self._auto_close_var,
                         command=self._on_action_opts_changed).pack(side=tk.LEFT, padx=6)

        # ── Tabs ───────────────────────────────────────────────────────────────
        self._tabs = ctk.CTkTabview(content)
        self._tabs.pack(fill=tk.BOTH, expand=True)

        for tab_name in ("  VR 设置  Settings  ", "  性能  Performance  ", "  日志  Log  "):
            self._tabs.add(tab_name)

        self._build_vr_tab(self._tabs.tab("  VR 设置  Settings  "))
        self._build_perf_tab(self._tabs.tab("  性能  Performance  "))
        self._build_log_tab(self._tabs.tab("  日志  Log  "))

        # ── Bottom bar ─────────────────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray85", "gray17"))
        bottom.pack(fill=tk.X, side=tk.BOTTOM)

        ctk.CTkButton(bottom, text="💾  保存  Save", width=110,
                       fg_color=("#2d7a2d", "#1a5c1a"), hover_color=("#1e601e", "#124412"),
                       command=self._save_all).pack(side=tk.LEFT, padx=8, pady=6)
        ctk.CTkButton(bottom, text="↺  重置  Reset", width=110,
                       command=self._reset_all).pack(side=tk.LEFT, padx=2, pady=6)
        ctk.CTkButton(bottom, text="📂 打开配置目录", width=110,
                       fg_color=("#3b5998", "#2a437c"), hover_color=("#4c70ba", "#345398"),
                       command=self._open_profile_dir).pack(side=tk.LEFT, padx=8, pady=6)

        ctk.CTkLabel(bottom,
                     text=f"v{VERSION}  ·  Wuthering Waves UEVR 注入器  ·  Based on UEVR framework by praydog",
                     font=ctk.CTkFont(size=9),
                     text_color="gray").pack(side=tk.RIGHT, padx=12, pady=6)

    # ── VR Settings tab ────────────────────────────────────────────────────────

    def _build_vr_tab(self, parent) -> None:
        left  = ctk.CTkFrame(parent, fg_color="transparent")
        right = ctk.CTkFrame(parent, fg_color="transparent")
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Runtime
        rt_frame = ctk.CTkFrame(left)
        rt_frame.pack(fill=tk.X, pady=(0, 8))

        ctk.CTkLabel(rt_frame, text="VR 运行时  Runtime",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))

        self._runtime_var = tk.StringVar()
        ctk.CTkRadioButton(rt_frame, text="OpenXR  (推荐 · Recommended)",
                            variable=self._runtime_var, value="0",
                            command=self._on_runtime_changed).pack(anchor=tk.W, padx=14, pady=2)
        ctk.CTkRadioButton(rt_frame, text="OpenVR  (SteamVR)",
                            variable=self._runtime_var, value="1",
                            command=self._on_runtime_changed).pack(anchor=tk.W, padx=14, pady=(2, 8))

        # Rendering method
        rm_frame = ctk.CTkFrame(left)
        rm_frame.pack(fill=tk.X, pady=(0, 8))

        ctk.CTkLabel(rm_frame, text="渲染模式  Rendering Method",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))

        self._render_var = tk.StringVar()
        for val, label in [
            ("0", "Native Stereo          (UE5 专用)"),
            ("1", "Synchronized Sequential (UE4 推荐 ✓)"),
            ("2", "Alternative             (画面问题时)"),
        ]:
            ctk.CTkRadioButton(rm_frame, text=label, variable=self._render_var, value=val,
                                command=self._on_vr_settings_changed).pack(anchor=tk.W, padx=14, pady=2)
        ctk.CTkFrame(rm_frame, height=4, fg_color="transparent").pack()

        # Options
        opts_frame = ctk.CTkFrame(left)
        opts_frame.pack(fill=tk.X)

        ctk.CTkLabel(opts_frame, text="选项  Options",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))

        self._nullify_var        = tk.BooleanVar()
        self._fps_var            = tk.BooleanVar()
        self._ue4compat_var      = tk.BooleanVar(value=True)
        self._extreme_compat_var = tk.BooleanVar(value=False)

        ctk.CTkCheckBox(opts_frame, text="UE4 兼容模式  (SkipPostInitProperties)",
                         variable=self._ue4compat_var,
                         command=self._on_vr_settings_changed).pack(anchor=tk.W, padx=14, pady=2)
        ctk.CTkCheckBox(opts_frame, text="极度兼容  Extreme Compatibility",
                         variable=self._extreme_compat_var,
                         command=self._on_vr_settings_changed).pack(anchor=tk.W, padx=14, pady=2)
        ctk.CTkCheckBox(opts_frame, text="禁用冲突插件  Nullify Conflicting Plugins",
                         variable=self._nullify_var,
                         command=self._on_nullify_changed).pack(anchor=tk.W, padx=14, pady=2)
        ctk.CTkCheckBox(opts_frame, text="显示 FPS 叠加层  Show FPS Overlay",
                         variable=self._fps_var,
                         command=self._on_vr_settings_changed).pack(anchor=tk.W, padx=14, pady=2)

        ctk.CTkLabel(opts_frame, text="UE4 compat: 鸣潮为 UE4，必须勾选否则 Fatal Error 崩溃",
                     font=ctk.CTkFont(size=9), text_color="orange").pack(anchor=tk.W, padx=14, pady=(6, 1))
        ctk.CTkLabel(opts_frame, text="Extreme: ACE 反作弊崩溃时启用  |  Nullify: 禁用冲突插件",
                     font=ctk.CTkFont(size=9), text_color="gray").pack(anchor=tk.W, padx=14, pady=(0, 8))

        # DLL list
        dll_frame = ctk.CTkFrame(right)
        dll_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 4))

        ctk.CTkLabel(dll_frame, text="注入 DLL 列表  Injection DLL List",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))

        self._dll_scroll = ctk.CTkScrollableFrame(dll_frame, height=160)
        self._dll_scroll.pack(fill=tk.BOTH, expand=True, padx=8, pady=4)

        self._dll_labels: list[ctk.CTkLabel] = []

        ctk.CTkLabel(right, text="UEVRPluginNullifier 始终第一 · UEVRBackend 始终最后",
                     font=ctk.CTkFont(size=9), text_color="gray").pack(anchor=tk.W, pady=2)

    # ── Performance tab ────────────────────────────────────────────────────────

    def _build_perf_tab(self, parent) -> None:
        scroll = ctk.CTkScrollableFrame(parent)
        scroll.pack(fill=tk.BOTH, expand=True)

        # Screen percentage
        sp_frame = ctk.CTkFrame(scroll)
        sp_frame.pack(fill=tk.X, pady=(0, 6), padx=4)
        ctk.CTkLabel(sp_frame, text="渲染分辨率  Render Resolution",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))

        self._sp_var = self._make_slider(
            sp_frame, "内部分辨率%  Screen Percentage", "Core_r.ScreenPercentage",
            self.cfg.cvars_standard, lo=10.0, hi=200.0, default=100.0, float_mode=True
        )

        # Quality
        q_frame = ctk.CTkFrame(scroll)
        q_frame.pack(fill=tk.X, pady=(0, 6), padx=4)
        ctk.CTkLabel(q_frame, text="质量设置  Quality Settings",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))

        for label, key, lo, hi, default, is_float in [
            ("分辨率质量  Resolution Quality", "sg.ResolutionQuality",        0, 100, 100.0, True),
            ("视野距离    View Distance",       "sg.ViewDistanceQuality",       0,   4,   2.0, False),
            ("抗锯齿      Anti-Aliasing",       "sg.AntiAliasingQuality",       0,   4,   2.0, False),
            ("后处理      Post Process",        "sg.PostProcessQuality",        0,   4,   2.0, False),
            ("阴影        Shadows",             "sg.ShadowQuality",             0,   4,   2.0, False),
            ("贴图        Textures",            "sg.TextureQuality",            0,   4,   2.0, False),
            ("特效        Effects",             "sg.EffectsQuality",            0,   4,   2.0, False),
            ("植被        Foliage",             "sg.FoliageQuality",            0,   4,   2.0, False),
            ("着色        Shading",             "sg.ShadingQuality",            0,   4,   2.0, False),
            ("反射质量    Reflection Quality",  "sg.ReflectionQuality",         0,   4,   2.0, False),
            ("全局光照    Global Illumination", "sg.GlobalIlluminationQuality", 0,   3,   2.0, False),
        ]:
            try:
                cur = float(self.cfg.user_script.get(key, str(default)))
            except ValueError:
                cur = default
            self._make_slider(q_frame, label, key, self.cfg.user_script, lo, hi, cur, float_mode=is_float)

        # Technical
        tc_frame = ctk.CTkFrame(scroll)
        tc_frame.pack(fill=tk.X, pady=(0, 6), padx=4)
        ctk.CTkLabel(tc_frame, text="技术设置  Technical Settings",
                     font=ctk.CTkFont(size=11, weight="bold")).pack(anchor=tk.W, padx=10, pady=(8, 4))

        for label, key, lo, hi, default in [
            ("垂直同步    VSync",            "r.VSync",           0, 3, 1.0),
            ("体积云      Volumetric Cloud", "r.VolumetricCloud",  0, 1, 0.0),
            ("反射方式    Reflection Method","r.ReflectionMethod", 0, 2, 0.0),
        ]:
            try:
                cur = float(self.cfg.user_script.get(key, str(default)))
            except ValueError:
                cur = default
            self._make_slider(tc_frame, label, key, self.cfg.user_script, lo, hi, cur)

    def _make_slider(self, parent, label: str, key: str,
                     data: dict, lo: float, hi: float,
                     default: float, float_mode: bool = False) -> tk.DoubleVar:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill=tk.X, padx=10, pady=3)

        ctk.CTkLabel(row, text=label, width=250, anchor="w",
                     font=ctk.CTkFont(size=10)).pack(side=tk.LEFT)

        val_text  = f"{default:.1f}" if float_mode else str(int(default))
        val_label = ctk.CTkLabel(row, text=val_text, width=55,
                                  font=ctk.CTkFont(family="Consolas", size=10))
        val_label.pack(side=tk.RIGHT)

        var = tk.DoubleVar(value=default)

        def _on_change(v: str) -> None:
            fv = float(v)
            if float_mode:
                display   = f"{fv:.1f}"
                data[key] = display
                val_label.configure(text=display)
            else:
                iv        = int(fv)
                data[key] = str(iv)
                val_label.configure(text=str(iv))

        sl = ctk.CTkSlider(row, from_=lo, to=hi, variable=var, command=_on_change)
        sl.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)

        if key in data:
            try:
                sl.set(float(data[key]))
            except (ValueError, TypeError):
                sl.set(default)

        self._sliders.append((sl, default))
        return var

    # ── Log tab ────────────────────────────────────────────────────────────────

    def _build_log_tab(self, parent) -> None:
        self._log_text = ctk.CTkTextbox(
            parent, font=ctk.CTkFont(family="Consolas", size=10),
            wrap="word", state="disabled"
        )
        self._log_text.pack(fill=tk.BOTH, expand=True)

        btn_row = ctk.CTkFrame(parent, fg_color="transparent")
        btn_row.pack(fill=tk.X, pady=(4, 0))
        ctk.CTkButton(btn_row, text="清空  Clear", width=100,
                       command=self._clear_log).pack(side=tk.RIGHT)

    # ── Populate UI from config ────────────────────────────────────────────────

    def _update_ui_from_config(self) -> None:
        cfg = self.cfg
        self._auto_inject_var.set(cfg.injector_config.get("custom_var_auto_inject") == "1")
        self._auto_focus_var.set(cfg.injector_config.get("custom_var_auto_focus")   == "1")
        self._auto_close_var.set(cfg.injector_config.get("custom_var_auto_close")   == "1")
        self._delay_var.set(cfg.injector_config.get("custom_var_inject_delay", "1"))

        self._runtime_var.set(cfg.injector_config.get("custom_var_runtime", "0"))
        self._render_var.set(cfg.config_txt.get("VR_RenderingMethod", "1"))
        self._nullify_var.set(cfg.injector_config.get("custom_var_nullify") == "1")
        self._fps_var.set(cfg.config_txt.get("VR_ShowFPSOverlay", "true").lower() == "true")
        self._ue4compat_var.set(
            cfg.config_txt.get("VR_Compatibility_SkipPostInitProperties", "true").lower() == "true"
        )
        self._extreme_compat_var.set(
            cfg.config_txt.get("VR_ExtremeCompatibilityMode", "false").lower() == "true"
        )
        self._refresh_dll_list()

    # ── DLL list helpers ───────────────────────────────────────────────────────

    def _refresh_dll_list(self) -> None:
        for lbl in self._dll_labels:
            lbl.destroy()
        self._dll_labels.clear()

        for dll in self.cfg.get_dll_list():
            lbl = ctk.CTkLabel(
                self._dll_scroll, text=f"  {dll}", anchor="w",
                font=ctk.CTkFont(family="Consolas", size=10),
                fg_color="transparent"
            )
            lbl.pack(fill=tk.X, pady=1)
            self._dll_labels.append(lbl)

    # ── Event handlers ─────────────────────────────────────────────────────────

    def _on_runtime_changed(self) -> None:
        self.cfg.set_runtime(self._runtime_var.get())
        self._refresh_dll_list()
        self._save_all()

    def _on_nullify_changed(self) -> None:
        self.cfg.set_nullify(self._nullify_var.get())
        self._refresh_dll_list()
        self._save_all()

    def _on_vr_settings_changed(self) -> None:
        self.cfg.config_txt["VR_RenderingMethod"]      = self._render_var.get()
        self.cfg.config_txt["VR_StereoRenderingMethod"] = self._render_var.get()
        self.cfg.config_txt["VR_ShowFPSOverlay"]        = "true" if self._fps_var.get() else "false"
        self.cfg.config_txt["VR_Compatibility_SkipPostInitProperties"] = (
            "true" if self._ue4compat_var.get() else "false"
        )
        self.cfg.config_txt["VR_ExtremeCompatibilityMode"] = (
            "true" if self._extreme_compat_var.get() else "false"
        )
        self._save_all()

    def _on_action_opts_changed(self) -> None:
        self.cfg.injector_config["custom_var_auto_inject"] = "1" if self._auto_inject_var.get() else "0"
        self.cfg.injector_config["custom_var_auto_focus"]  = "1" if self._auto_focus_var.get() else "0"
        self.cfg.injector_config["custom_var_auto_close"]  = "1" if self._auto_close_var.get() else "0"
        try:
            self.cfg.injector_config["custom_var_inject_delay"] = str(self._delay_var.get())
        except Exception:
            pass
        self.cfg.save_all()

    def _save_all(self) -> None:
        self.cfg.injector_config["custom_var_runtime"]       = self._runtime_var.get()
        self.cfg.config_txt["VR_RenderingMethod"]            = self._render_var.get()
        self.cfg.config_txt["VR_StereoRenderingMethod"]      = self._render_var.get()
        self.cfg.config_txt["VR_ShowFPSOverlay"]             = "true" if self._fps_var.get() else "false"
        self.cfg.config_txt["VR_Compatibility_SkipPostInitProperties"] = (
            "true" if self._ue4compat_var.get() else "false"
        )
        self.cfg.config_txt["VR_ExtremeCompatibilityMode"]  = (
            "true" if self._extreme_compat_var.get() else "false"
        )
        self.cfg.injector_config["custom_var_auto_inject"]  = "1" if self._auto_inject_var.get() else "0"
        self.cfg.injector_config["custom_var_auto_focus"]   = "1" if self._auto_focus_var.get() else "0"
        self.cfg.injector_config["custom_var_auto_close"]   = "1" if self._auto_close_var.get() else "0"
        try:
            self.cfg.injector_config["custom_var_inject_delay"] = str(self._delay_var.get())
        except Exception:
            pass
        self.cfg.save_all()
        self._log("[LOG] Settings saved.")

    def _reset_all(self) -> None:
        if messagebox.askyesno("重置设置  Reset Settings",
                                "重置所有设置为默认值？\nReset all settings to defaults?"):
            self.cfg.reset_defaults()
            self.cfg.save_all()
            self._update_ui_from_config()
            # Re-position all sliders to their defaults (triggers _on_change → updates data dict)
            for sl, default in self._sliders:
                sl.set(default)
            self._log("[LOG] Settings reset to defaults.")

    def _open_profile_dir(self) -> None:
        """Open the UEVR profile directory in Explorer."""
        self.cfg.ensure_profile_exists()
        try:
            os.startfile(self.cfg.profile_path)
            self._log(f"[LOG] Opened profile directory: {self.cfg.profile_path}")
        except Exception as e:
            self._log(f"[ERROR] Could not open profile directory: {e}")

    # ── Log helpers ────────────────────────────────────────────────────────────

    def _log(self, message: str) -> None:
        def _update() -> None:
            self._log_text.configure(state="normal")
            self._log_text.insert("end", message + "\n")
            self._log_text.see("end")
            self._log_text.configure(state="disabled")
        try:
            self.after(0, _update)
        except Exception:
            pass

    def _clear_log(self) -> None:
        self._log_text.configure(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.configure(state="disabled")

    # ── Process monitor ────────────────────────────────────────────────────────

    def _start_monitor(self) -> None:
        self._monitoring = True
        threading.Thread(target=self._monitor_loop, daemon=True).start()

    def _monitor_loop(self) -> None:
        prev_pid: int | None = None
        while self._monitoring:
            try:
                pid = self.injector.find_process_pid(GAME_EXE)
                if pid != prev_pid:
                    prev_pid      = pid
                    self.game_pid = pid
                    self.after(0, lambda p=pid: self._update_status(p))
                    if pid:
                        self._log(f"[LOG] Game detected  PID={pid}")
                        self._already_injected = False
                        if self._auto_inject_var.get():
                            try:
                                delay = int(self._delay_var.get())
                            except Exception:
                                delay = 1
                            if delay > 0:
                                time.sleep(delay)
                            if self.game_pid == pid:
                                self.after(0, self._do_inject)
                    else:
                        self._already_injected = False
                        self._log("[LOG] Game process exited.")
            except Exception:
                pass
            time.sleep(2)

    def _update_status(self, pid: int | None) -> None:
        if pid:
            self._status_dot.configure(text_color="green")
            self._status_label.configure(text=f"游戏运行中  Running  PID={pid}")
        else:
            self._status_dot.configure(text_color="red")
            self._status_label.configure(text="游戏未运行  Game Not Running")
            # Game exited → injection state resets
            self._update_inject_status(False)

    def _update_inject_status(self, injected: bool) -> None:
        if injected:
            self._inject_dot.configure(text_color="#a6e3a1")   # green
            self._inject_label.configure(text="已注入  Injected ✔")
        else:
            self._inject_dot.configure(text_color="gray")
            self._inject_label.configure(text="未注入  Not Injected")

    # ── Injection ──────────────────────────────────────────────────────────────

    def _do_inject(self) -> None:
        pid = self.game_pid or self.injector.find_process_pid(GAME_EXE)
        if not pid:
            messagebox.showerror("游戏未运行",
                                  f"未检测到游戏进程。\nGame not running.\n\nPlease start {GAME_EXE} first.")
            return
        if self._already_injected:
            if not messagebox.askyesno("已注入",
                                        "UEVR 可能已经注入。是否再次注入？\n"
                                        "UEVR may already be injected. Inject again?"):
                return

        self._save_all()
        self.cfg.ensure_profile_exists()
        self._inject_btn.configure(state="disabled", text="注入中…  Injecting…")

        def _worker() -> None:
            dll_list = self.cfg.get_dll_list()
            ok_count = 0
            self._log(f"[LOG] Injecting {len(dll_list)} DLL(s) into PID={pid} …")
            for dll_name in dll_list:
                dll_path = os.path.join(self.cfg.uevr_folder, dll_name)
                self._log(f"[LOG]  → {dll_name}")
                if self.injector.inject_dll(pid, dll_path):
                    ok_count += 1
                time.sleep(0.4)
            if ok_count > 0:
                self._log(f"[OK] Injection complete  ({ok_count}/{len(dll_list)} DLLs succeeded)")
                self._already_injected = True
                self.after(0, lambda: self._update_inject_status(True))
                if self._auto_focus_var.get():
                    self.injector.focus_process(GAME_EXE)
                if self._auto_close_var.get():
                    self._log("[LOG] Auto-close: shutting down launcher …")
                    time.sleep(1.5)
                    self.after(0, self.destroy)
            else:
                self._log("[ERROR] All injections failed.  Run the launcher as Administrator and try again.")
                self.after(0, lambda: self._update_inject_status(False))
            self.after(0, lambda: self._inject_btn.configure(
                state="normal", text="💉  注入 VR  Inject VR"))

        threading.Thread(target=_worker, daemon=True).start()

    def on_close(self) -> None:
        self._monitoring = False
        self._save_all()
        self.destroy()


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if sys.platform != "win32":
        print("ERROR: This application only runs on Windows.")
        sys.exit(1)
    app = App()
    app.protocol("WM_DELETE_WINDOW", app.on_close)
    app.mainloop()


if __name__ == "__main__":
    main()

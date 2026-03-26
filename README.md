# 鸣潮 VR 启动器 (Wuthering Waves VR Launcher)

An easy-to-use UEVR launcher and configurator specifically designed for Wuthering Waves, featuring one-click injection and optimized VR compatibility settings.

专为《鸣潮》设计的易用型 UEVR 启动器与配置工具，提供一键注入和优化的 VR 兼容性设置。

演示视频：https://www.bilibili.com/video/BV12NX4BEE3M


## ✨ 核心特性 

*   **一键自动注入**: 自动检测游戏进程并一键注入 UEVR。
*   **最佳兼容性预设**: 内置针对《鸣潮》优化的 UEVR 渲染参数，防止注入崩溃。
*   **现代化界面**: 基于 `customtkinter` 打造的无边框暗色现代 GUI。

## 🛠️ 安装与使用

### 测试环境
*   **操作系统**: Windows 10
*   **VR 头显**: Meta Quest 3
*   **串流软件**: Virtual Desktop (VD) 1.23.19
*   **鸣潮版本**: 国际服 OS WindowsPr0duct 3.2.0 6711429 3.2.9 6770228

### 运行步骤
1.  克隆或下载本仓库到本地。
2.  安装必需的依赖库：
    ```bash
    pip install -r requirements.txt
    ```
3.  戴上 VR 头显并连接好 Virtual Desktop。
4.  通过批处理文件 `Run_WW_VR.bat` 启动。
5.  启动《鸣潮》游戏主程序。
6.  在启动器界面等待自动注入或点击“注入”按钮。

## 🚨 当前已知问题

目前在适配《鸣潮》VR 模式时，存在以下由于游戏魔改渲染管线导致的、尚未解决的视觉体验问题：

### 1. VR 设备内 UI 双眼重影
在 VR 头显中游玩时，由于游戏原生渲染管线的特殊性，双眼各自都会单独生成一个完整的游戏内 UI。视线右上方还有一个红点。

### 2. PC 屏幕端画面变形与 Logo 闪烁
注入 UEVR 之后，虽然 VR 端有 3D 画面，但在电脑 PC 端的显示器上，整体游戏界面往往会发生变形拉伸，并伴随着一个持续闪烁的 “库洛” 标志。

## ⚠️ 免责声明

本工具仅为辅助调用并写入 UEVR 开源组件的启动器脚本，**不包含**任何破坏性内存修改或作弊功能。但《鸣潮》带有底层的反作弊检测（ACE等），任何形式的第三方进程挂钩有可能带来未知的封号风险。**请玩家自行承担使用本项目的账号安全风险（如需测试请尽量使用小号）。**

## 鸣谢 (Credits & References)

*   **[UEVR](https://github.com/praydog/UEVR)** by Praydog - 感谢开源的 Universal Unreal Engine VR Mod 框架。

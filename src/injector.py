"""
injector.py  -  Windows DLL injection engine for WW VR Launcher
Uses CreateRemoteThread + LoadLibraryW (standard injection technique).
"""
from __future__ import annotations

import ctypes
import ctypes.wintypes
import os
import sys
from typing import Callable, Optional

# ── Windows constants ──────────────────────────────────────────────────────────
PROCESS_ALL_ACCESS    = 0x1F0FFF
MEM_COMMIT            = 0x1000
MEM_RESERVE           = 0x2000
MEM_RELEASE           = 0x8000
PAGE_READWRITE        = 0x04
TH32CS_SNAPPROCESS    = 0x00000002
SW_RESTORE            = 9
INVALID_HANDLE_VALUE  = ctypes.c_void_p(-1).value
WAIT_TIMEOUT          = 0x00000102

GAME_EXE = "Client-Win64-Shipping.exe"


# ── PROCESSENTRY32W structure ──────────────────────────────────────────────────
class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize",             ctypes.wintypes.DWORD),
        ("cntUsage",           ctypes.wintypes.DWORD),
        ("th32ProcessID",      ctypes.wintypes.DWORD),
        ("th32DefaultHeapID",  ctypes.c_size_t),          # ULONG_PTR
        ("th32ModuleID",       ctypes.wintypes.DWORD),
        ("cntThreads",         ctypes.wintypes.DWORD),
        ("th32ParentProcessID",ctypes.wintypes.DWORD),
        ("pcPriClassBase",     ctypes.c_long),
        ("dwFlags",            ctypes.wintypes.DWORD),
        ("szExeFile",          ctypes.c_wchar * 260),
    ]


# ── DLLInjector ────────────────────────────────────────────────────────────────
class DLLInjector:
    """
    Injects DLLs into Windows processes using CreateRemoteThread / LoadLibraryW.
    All methods are safe to call from a background thread.
    """

    def __init__(self, log_callback: Optional[Callable[[str], None]] = None):
        self._log = log_callback or (lambda msg: None)
        self._k32  = ctypes.WinDLL("kernel32", use_last_error=True)
        self._u32  = ctypes.WinDLL("user32",   use_last_error=True)
        self._setup_k32_api()
        self._setup_u32_api()

    # ── API setup ──────────────────────────────────────────────────────────────

    def _setup_k32_api(self) -> None:
        k = self._k32
        HANDLE  = ctypes.wintypes.HANDLE
        DWORD   = ctypes.wintypes.DWORD
        BOOL    = ctypes.wintypes.BOOL
        LPCWSTR = ctypes.wintypes.LPCWSTR
        PVOID   = ctypes.c_void_p
        SIZE_T  = ctypes.c_size_t

        k.CreateToolhelp32Snapshot.restype  = HANDLE
        k.CreateToolhelp32Snapshot.argtypes = [DWORD, DWORD]

        k.Process32FirstW.restype  = BOOL
        k.Process32FirstW.argtypes = [HANDLE, ctypes.POINTER(PROCESSENTRY32W)]

        k.Process32NextW.restype   = BOOL
        k.Process32NextW.argtypes  = [HANDLE, ctypes.POINTER(PROCESSENTRY32W)]

        k.OpenProcess.restype  = HANDLE
        k.OpenProcess.argtypes = [DWORD, BOOL, DWORD]

        k.VirtualAllocEx.restype  = PVOID
        k.VirtualAllocEx.argtypes = [HANDLE, PVOID, SIZE_T, DWORD, DWORD]

        k.WriteProcessMemory.restype  = BOOL
        k.WriteProcessMemory.argtypes = [
            HANDLE, PVOID, PVOID, SIZE_T, ctypes.POINTER(SIZE_T)
        ]

        k.CreateRemoteThread.restype  = HANDLE
        k.CreateRemoteThread.argtypes = [
            HANDLE, PVOID, SIZE_T, PVOID, PVOID, DWORD, PVOID
        ]

        k.WaitForSingleObject.restype  = DWORD
        k.WaitForSingleObject.argtypes = [HANDLE, DWORD]

        k.GetExitCodeThread.restype  = BOOL
        k.GetExitCodeThread.argtypes = [HANDLE, ctypes.POINTER(DWORD)]

        k.VirtualFreeEx.restype  = BOOL
        k.VirtualFreeEx.argtypes = [HANDLE, PVOID, SIZE_T, DWORD]

        k.CloseHandle.restype  = BOOL
        k.CloseHandle.argtypes = [HANDLE]

        k.GetModuleHandleW.restype  = ctypes.wintypes.HMODULE
        k.GetModuleHandleW.argtypes = [LPCWSTR]

        k.GetProcAddress.restype  = PVOID
        k.GetProcAddress.argtypes = [ctypes.wintypes.HMODULE, ctypes.c_char_p]

    def _setup_u32_api(self) -> None:
        u = self._u32
        BOOL   = ctypes.wintypes.BOOL
        HWND   = ctypes.wintypes.HWND
        DWORD  = ctypes.wintypes.DWORD
        LPARAM = ctypes.wintypes.LPARAM
        INT    = ctypes.wintypes.INT

        WNDENUMPROC = ctypes.WINFUNCTYPE(BOOL, HWND, LPARAM)

        u.EnumWindows.restype  = BOOL
        u.EnumWindows.argtypes = [WNDENUMPROC, LPARAM]

        u.GetWindowThreadProcessId.restype  = DWORD
        u.GetWindowThreadProcessId.argtypes = [HWND, ctypes.POINTER(DWORD)]

        u.IsWindowVisible.restype  = BOOL
        u.IsWindowVisible.argtypes = [HWND]

        u.ShowWindowAsync.restype  = BOOL
        u.ShowWindowAsync.argtypes = [HWND, INT]

        u.SetForegroundWindow.restype  = BOOL
        u.SetForegroundWindow.argtypes = [HWND]

    # ── Public API ─────────────────────────────────────────────────────────────

    def find_process_pid(self, exe_name: str) -> Optional[int]:
        """Return the PID of a running process by executable name, or None."""
        k = self._k32
        snapshot = k.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
        if snapshot == INVALID_HANDLE_VALUE:
            return None

        try:
            entry = PROCESSENTRY32W()
            entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)

            if not k.Process32FirstW(snapshot, ctypes.byref(entry)):
                return None

            while True:
                if entry.szExeFile.lower() == exe_name.lower():
                    return entry.th32ProcessID
                if not k.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
        finally:
            k.CloseHandle(snapshot)

        return None

    def inject_dll(self, pid: int, dll_path: str) -> bool:
        """
        Inject *dll_path* into process *pid* via CreateRemoteThread.
        Returns True on success.
        """
        dll_path = os.path.abspath(dll_path)

        if not os.path.isfile(dll_path):
            self._log(f"[ERROR] DLL not found: {dll_path}")
            return False

        k = self._k32

        # Resolve LoadLibraryW in *our* process — valid for all processes in the
        # same boot session because kernel32 is mapped at the same ASLR base.
        h_k32 = k.GetModuleHandleW("kernel32.dll")
        if not h_k32:
            self._log("[ERROR] GetModuleHandleW(kernel32.dll) failed")
            return False

        load_lib_addr = k.GetProcAddress(h_k32, b"LoadLibraryW")
        if not load_lib_addr:
            self._log("[ERROR] GetProcAddress(LoadLibraryW) failed")
            return False

        h_proc = k.OpenProcess(PROCESS_ALL_ACCESS, False, pid)
        if not h_proc:
            err = ctypes.get_last_error()
            self._log(
                f"[ERROR] OpenProcess(PID {pid}) failed — error {err}. "
                "Try running the launcher as Administrator."
            )
            return False

        try:
            # Encode path as UTF-16-LE with null terminator
            path_bytes = (dll_path + "\0").encode("utf-16-le")
            path_len   = len(path_bytes)

            remote_mem = k.VirtualAllocEx(
                h_proc, None, path_len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
            )
            if not remote_mem:
                self._log("[ERROR] VirtualAllocEx failed")
                return False

            try:
                written = ctypes.c_size_t(0)
                buf = ctypes.create_string_buffer(path_bytes)
                ok  = k.WriteProcessMemory(
                    h_proc, remote_mem, buf, path_len, ctypes.byref(written)
                )
                if not ok or written.value != path_len:
                    self._log("[ERROR] WriteProcessMemory failed")
                    return False

                h_thread = k.CreateRemoteThread(
                    h_proc, None, 0,
                    ctypes.c_void_p(load_lib_addr),
                    ctypes.c_void_p(remote_mem),
                    0, None
                )
                if not h_thread:
                    self._log("[ERROR] CreateRemoteThread failed")
                    return False

                try:
                    ret = k.WaitForSingleObject(h_thread, 8000)  # 8 s timeout
                    if ret == WAIT_TIMEOUT:
                        self._log(f"[WARN] Timeout waiting for {os.path.basename(dll_path)}")

                    exit_code = ctypes.wintypes.DWORD(0)
                    k.GetExitCodeThread(h_thread, ctypes.byref(exit_code))

                    if exit_code.value == 0:
                        self._log(
                            f"[WARN] LoadLibraryW returned NULL for "
                            f"{os.path.basename(dll_path)} — already injected or load error?"
                        )
                        # Return True so callers don't abort — may already be loaded
                        return True

                    self._log(f"[OK] Injected: {os.path.basename(dll_path)}")
                    return True
                finally:
                    k.CloseHandle(h_thread)
            finally:
                k.VirtualFreeEx(h_proc, remote_mem, 0, MEM_RELEASE)
        finally:
            k.CloseHandle(h_proc)

    def focus_process(self, exe_name: str) -> bool:
        """Bring the main window of *exe_name* to the foreground."""
        pid = self.find_process_pid(exe_name)
        if not pid:
            return False

        u = self._u32
        found = ctypes.wintypes.HWND(0)
        target_pid = ctypes.wintypes.DWORD(pid)

        WNDENUMPROC = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM
        )

        @WNDENUMPROC
        def _cb(hwnd: ctypes.wintypes.HWND, _: ctypes.wintypes.LPARAM) -> bool:
            win_pid = ctypes.wintypes.DWORD(0)
            u.GetWindowThreadProcessId(hwnd, ctypes.byref(win_pid))
            if win_pid.value == target_pid.value and u.IsWindowVisible(hwnd):
                found.value = hwnd
                return False  # stop enumeration
            return True

        u.EnumWindows(_cb, 0)

        if found.value:
            u.ShowWindowAsync(found, SW_RESTORE)
            return bool(u.SetForegroundWindow(found))
        return False


def is_admin() -> bool:
    """Return True if the process is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False

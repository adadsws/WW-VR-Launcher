"""
config_manager.py  -  UEVR profile configuration manager for Wuthering Waves.

UEVR stores per-game profiles under:
  %APPDATA%\\UnrealVRMod\\<game_exe_without_extension>\\

Files managed:
  injector_config.txt   – launcher / injection options  (key=value)
  config.txt            – UEVR runtime options           (key=value)
  cvars_standard.txt    – engine console variables       (key=value)
  user_script.txt       – UE console commands on startup (key value)
"""

import os
from typing import Dict, List, Optional

# ── Game identity ──────────────────────────────────────────────────────────────
GAME_EXE     = "Client-Win64-Shipping.exe"
PROFILE_NAME = "Client-Win64-Shipping"        # exe without extension

PROFILES_ROOT = os.path.join(
    os.environ.get("APPDATA", os.path.expanduser("~")), "UnrealVRMod"
)

# ── Default values (pre-tuned for Wuthering Waves / UE5) ─────────────────────
_DEFAULT_INJECTOR: Dict[str, str] = {
    "custom_var_runtime":      "0",    # 0 = OpenXR, 1 = OpenVR/SteamVR
    "custom_var_nullify":      "0",    # 1 = inject UEVRPluginNullifier first
    "custom_var_auto_inject":  "1",    # 1 = inject automatically on game start
    "custom_var_auto_focus":   "1",    # 1 = focus game window after injection
    "custom_var_auto_close":   "0",    # 1 = close launcher after injection
    "custom_var_urvr_folder":  "null", # path to UEVR folder
    "custom_var_last_pid":     "null",
}

_DEFAULT_CONFIG: Dict[str, str] = {
    "VR_RenderingMethod":                       "1",     # 0=Native(UE5), 1=Sync Seq(UE4), 2=Alt
    "VR_ShowFPSOverlay":                        "true",
    "VR_EnableDepthBufferCapture":              "false",
    "VR_Compatibility_SkipPostInitProperties":  "true",   # required for most UE4 games
    "VR_StereoRenderingMethod":                 "1",      # Sync Sequential for UE4
    "VR_SyncedSequentialMethod":                "1",
    "VR_UncapFramerate":                        "true",
    "VR_DisableHZBOcclusion":                   "true",
    "VR_DisableInstanceCulling":                "true",
    "VR_DesktopRecordingFix_V2":                "true",
    "VR_DisableHDRCompositing":                 "true",
}

_DEFAULT_CVARS: Dict[str, str] = {
    "Core_r.ScreenPercentage": "100.0",
}

# user_script.txt uses "key value" (space-separated), not "key=value"
_DEFAULT_SCRIPT: Dict[str, str] = {
    "sg.ResolutionQuality":           "100.0",
    "sg.ViewDistanceQuality":         "2",
    "sg.AntiAliasingQuality":         "2",
    "sg.PostProcessQuality":          "2",
    "sg.ShadowQuality":               "2",
    "sg.TextureQuality":              "2",
    "sg.EffectsQuality":              "2",
    "sg.FoliageQuality":              "2",
    "sg.ShadingQuality":              "2",
    "sg.ReflectionQuality":           "2",
    "r.VSync":                        "1",
    "r.VolumetricCloud":              "0",
    "sg.GlobalIlluminationQuality":   "2",
    "r.ReflectionMethod":             "0",
}

_DEFAULT_DLLS: List[str] = [
    "openxr_loader.dll",
    "UEVRBackend.dll",
]


# ── ConfigManager ──────────────────────────────────────────────────────────────
class ConfigManager:
    """Read and write UEVR profile config files for Wuthering Waves."""

    def __init__(self) -> None:
        self.profile_path  = os.path.join(PROFILES_ROOT, PROFILE_NAME)
        self.uevr_folder:  Optional[str] = None

        # Mutable config dictionaries (keys → string values)
        self.injector_config: Dict[str, str] = {}
        self.config_txt:      Dict[str, str] = {}
        self.cvars_standard:  Dict[str, str] = {}
        self.user_script:     Dict[str, str] = {}
        self.dll_files:       List[str]       = []

        self.reset_defaults()

    # ── Defaults ───────────────────────────────────────────────────────────────

    def reset_defaults(self) -> None:
        # Update in-place so slider closures that captured these dicts stay valid
        self.injector_config.clear(); self.injector_config.update(_DEFAULT_INJECTOR)
        self.config_txt.clear();      self.config_txt.update(_DEFAULT_CONFIG)
        self.cvars_standard.clear();  self.cvars_standard.update(_DEFAULT_CVARS)
        self.user_script.clear();     self.user_script.update(_DEFAULT_SCRIPT)
        self.dll_files.clear();       self.dll_files.extend(_DEFAULT_DLLS)
        self.uevr_folder = None

    # ── File I/O ───────────────────────────────────────────────────────────────

    def ensure_profile_exists(self) -> bool:
        """Create profile directory and empty config files if missing."""
        try:
            os.makedirs(self.profile_path, exist_ok=True)
            for name in (
                "injector_config.txt",
                "config.txt",
                "cvars_standard.txt",
                "user_script.txt",
            ):
                path = os.path.join(self.profile_path, name)
                if not os.path.exists(path):
                    open(path, "w").close()
            return True
        except OSError:
            return False

    @staticmethod
    def _read_kv(filepath: str, sep: str = "=") -> Dict[str, str]:
        """Parse a key<sep>value text file, ignoring blank lines / comments."""
        result: Dict[str, str] = {}
        try:
            with open(filepath, "r", encoding="utf-8") as fh:
                for raw in fh:
                    line = raw.strip()
                    if not line or line.startswith("#"):
                        continue
                    parts = line.split(sep, 1)
                    if len(parts) == 2:
                        result[parts[0].strip()] = parts[1].strip()
        except (OSError, UnicodeDecodeError):
            pass
        return result

    @staticmethod
    def _write_kv(filepath: str, data: Dict[str, str], sep: str = "=") -> None:
        """Write key<sep>value text file."""
        with open(filepath, "w", encoding="utf-8") as fh:
            for key, value in data.items():
                fh.write(f"{key}{sep}{value}\n")

    def load_all(self) -> None:
        """Load all config files from the profile directory into memory."""
        p = self.profile_path

        saved_inj = self._read_kv(os.path.join(p, "injector_config.txt"))
        if saved_inj:
            self.injector_config.update(saved_inj)

        saved_cfg = self._read_kv(os.path.join(p, "config.txt"))
        if saved_cfg:
            self.config_txt.update(saved_cfg)

        saved_cv = self._read_kv(os.path.join(p, "cvars_standard.txt"))
        if saved_cv:
            self.cvars_standard.update(saved_cv)

        # user_script uses space separator
        saved_sc = self._read_kv(os.path.join(p, "user_script.txt"), sep=" ")
        if saved_sc:
            self.user_script.update(saved_sc)

        # Restore UEVR folder path
        uevr = self.injector_config.get("custom_var_urvr_folder", "null")
        self.uevr_folder = uevr if (uevr != "null" and os.path.isdir(uevr)) else None

        # Rebuild DLL list: if nullify was enabled, prepend nullifier
        if self.injector_config.get("custom_var_nullify") == "1":
            if "UEVRPluginNullifier.dll" not in self.dll_files:
                self.dll_files.insert(0, "UEVRPluginNullifier.dll")

        # Sync runtime → DLL selection
        self._sync_runtime_dll(self.injector_config.get("custom_var_runtime", "0"))

    def save_all(self) -> None:
        """Write all config dictionaries back to disk."""
        self.ensure_profile_exists()
        p = self.profile_path

        self.injector_config["custom_var_urvr_folder"] = (
            self.uevr_folder if self.uevr_folder else "null"
        )

        self._write_kv(os.path.join(p, "injector_config.txt"), self.injector_config)
        self._write_kv(os.path.join(p, "config.txt"),          self.config_txt)
        self._write_kv(os.path.join(p, "cvars_standard.txt"),  self.cvars_standard)
        self._write_kv(os.path.join(p, "user_script.txt"),     self.user_script, sep=" ")

    # ── DLL management ─────────────────────────────────────────────────────────

    def get_dll_list(self) -> List[str]:
        """
        Return the ordered DLL list:
          UEVRPluginNullifier.dll  (first, if enabled)
          … other DLLs …
          UEVRBackend.dll          (last, always)
        """
        nullifier = "UEVRPluginNullifier.dll"
        backend   = "UEVRBackend.dll"

        middle = [d for d in self.dll_files if d not in (nullifier, backend)]
        result = []

        if nullifier in self.dll_files:
            result.append(nullifier)
        result.extend(middle)
        if backend in self.dll_files:
            result.append(backend)
        else:
            result.append(backend)   # backend is always required

        return result

    def set_runtime(self, runtime: str) -> None:
        """
        Switch VR runtime.
          '0' → OpenXR   (openxr_loader.dll)
          '1' → OpenVR   (openvr_api.dll / SteamVR)
        Updates injector_config and adjusts dll_files accordingly.
        """
        self.injector_config["custom_var_runtime"] = runtime
        self._sync_runtime_dll(runtime)

    def _sync_runtime_dll(self, runtime: str) -> None:
        if runtime == "0":   # OpenXR
            self._remove_dll("openvr_api.dll")
            self._add_dll_after_nullifier("openxr_loader.dll")
        else:                # OpenVR
            self._remove_dll("openxr_loader.dll")
            self._add_dll_after_nullifier("openvr_api.dll")

    def set_nullify(self, enabled: bool) -> None:
        """Toggle UEVRPluginNullifier.dll in the injection list."""
        self.injector_config["custom_var_nullify"] = "1" if enabled else "0"
        if enabled:
            if "UEVRPluginNullifier.dll" not in self.dll_files:
                self.dll_files.insert(0, "UEVRPluginNullifier.dll")
        else:
            self._remove_dll("UEVRPluginNullifier.dll")

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _remove_dll(self, name: str) -> None:
        try:
            self.dll_files.remove(name)
        except ValueError:
            pass

    def _add_dll_after_nullifier(self, name: str) -> None:
        if name in self.dll_files:
            return
        nullifier = "UEVRPluginNullifier.dll"
        if nullifier in self.dll_files:
            idx = self.dll_files.index(nullifier) + 1
        else:
            idx = 0
        self.dll_files.insert(idx, name)

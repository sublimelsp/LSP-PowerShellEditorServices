import os
import shutil
import subprocess
import tempfile

from urllib.request import urlretrieve
from zipfile import ZipFile

import sublime

from LSP.plugin import AbstractPlugin
from LSP.plugin import ClientConfig
from LSP.plugin import WorkspaceFolder
from LSP.plugin.core.typing import Any, List, Optional

URL = "https://github.com/PowerShell/PowerShellEditorServices/releases/download/v{}/PowerShellEditorServices.zip"


class PowerShellEditorServices(AbstractPlugin):

    # ---- public API methods ----

    @classmethod
    def name(cls) -> str:
        return cls.__name__

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        try:
            cmd = '[System.Diagnostics.FileVersionInfo]::GetVersionInfo("{}").FileVersion'.format(cls.dll_path())
            version_info = cls.run(cls.powershell_exe(), "-Command", cmd).decode('ascii')
            version_info = ".".join(version_info.splitlines()[0].strip().split('.')[0:3])
            return cls.version_str() != version_info
        except Exception:
            pass
        return True

    @classmethod
    def install_or_update(cls) -> None:
        shutil.rmtree(cls.basedir(), ignore_errors=True)
        os.makedirs(cls.storage_path(), exist_ok=True)
        try:
            zipfile = os.path.join(cls.storage_path(), "{}.zip".format(cls.name()))
            urlretrieve(URL.format(cls.version_str()), zipfile)
            with ZipFile(zipfile, "r") as f:
                f.extractall(cls.basedir())
            os.unlink(zipfile)
        except Exception:
            shutil.rmtree(cls.basedir(), ignore_errors=True)
            raise

    @classmethod
    def can_start(cls, window: sublime.Window, initiating_view: sublime.View,
                  workspace_folders: List[WorkspaceFolder], configuration: ClientConfig) -> Optional[str]:
        if not configuration.command:
            if sublime.platform() == "windows":
                configuration.command = cls.get_windows_command()
            else:
                configuration.command = cls.get_unix_command()

        return super().can_start(window, initiating_view, workspace_folders, configuration)

    def m_powerShell_executionStatusChanged(self, params: Any) -> None:
        pass

    # ---- internal methods -----

    @classmethod
    def get_windows_command(cls) -> List[str]:
        return [
            cls.powershell_exe(),
            "-NoLogo",
            "-NoProfile",
            "-File",
            cls.start_script(),
            "-BundledModulesPath",
            cls.bundled_modules_path(),
            "-HostName",
            "SublimeText",
            "-HostProfileId",
            "SublimeText",
            "-HostVersion",
            cls.host_version(),
            "-Stdio",
            "-LogPath",
            cls.log_path(),
            "-SessionDetailsPath",
            cls.session_details_path(),
        ]

    @classmethod
    def get_unix_command(cls) -> List[str]:
        return [
            cls.powershell_exe(),
            "-NoLogo",
            "-NoProfile",
            cls.start_script(),
            "-BundledModulesPath",
            cls.bundled_modules_path(),
            "-HostName",
            "SublimeText",
            "-HostProfileId",
            "SublimeText",
            "-HostVersion",
            cls.host_version(),
            "-Stdio",
            "-LogPath",
            cls.log_path(),
            "-SessionDetailsPath",
            cls.session_details_path(),
            "-FeatureFlags",
            "PSReadLine"
        ]

    @classmethod
    def basedir(cls) -> str:
        return os.path.join(cls.storage_path(), "LSP-{}".format(cls.name()))

    @classmethod
    def start_script(cls) -> str:
        return os.path.join(cls.basedir(), "PowerShellEditorServices", "Start-EditorServices.ps1")

    @classmethod
    def host_version(cls) -> str:
        return "{}.0.0".format(sublime.version())

    @classmethod
    def session_details_path(cls) -> str:
        return os.path.join(tempfile.gettempdir(), "{}.json".format(cls.name()))

    @classmethod
    def log_path(cls) -> str:
        return os.path.join(tempfile.gettempdir(), "{}.log".format(cls.name()))

    @classmethod
    def bundled_modules_path(cls) -> str:
        return cls.basedir()

    @classmethod
    def dll_path(cls) -> str:
        return os.path.join(
            cls.basedir(),
            "PowerShellEditorServices",
            "bin",
            "Common",
            "Microsoft.PowerShell.EditorServices.dll"
        )

    @classmethod
    def version_str(cls) -> str:
        settings = sublime.load_settings("LSP-{}.sublime-settings".format(cls.name()))
        return str(settings.get("version"))

    @classmethod
    def powershell_exe(cls) -> str:
        settings = sublime.load_settings("LSP-{}.sublime-settings".format(cls.name()))
        powershell_exe = settings.get("powershell_exe")
        if isinstance(powershell_exe, str) and powershell_exe:
            return powershell_exe
        return {
            "linux": "pwsh",
            "windows": "powershell.exe",
            "osx": "pwsh"
        }[sublime.platform()]

    @classmethod
    def run(cls, *args: Any, **kwargs: Any) -> bytes:
        if sublime.platform() == "windows":
            startupinfo = subprocess.STARTUPINFO()  # type: ignore
            flag = subprocess.STARTF_USESHOWWINDOW  # type: ignore
            startupinfo.dwFlags |= flag
        else:
            startupinfo = None
        return subprocess.check_output(args=args, cwd=kwargs.get("cwd"), startupinfo=startupinfo)

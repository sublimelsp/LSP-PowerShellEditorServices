from urllib.request import urlretrieve
from zipfile import ZipFile
import os
import shutil
import subprocess
import tempfile

from LSP.plugin import AbstractPlugin
from LSP.plugin.core.typing import Any, Dict, Optional, Tuple, List
import sublime

URL = "https://github.com/PowerShell/PowerShellEditorServices/releases/download/v{}/PowerShellEditorServices.zip"


class PowerShellEditorServices(AbstractPlugin):
    @classmethod
    def name(cls) -> str:
        return cls.__name__

    @classmethod
    def configuration(cls) -> Tuple[sublime.Settings, str]:
        settings, file_path = super().configuration()
        if sublime.platform() == "windows":
            settings.set("command", cls.get_windows_command())
        else:
            settings.set("command", cls.get_unix_command())
        return settings, file_path

    @classmethod
    def get_windows_command(cls) -> List[str]:
        return [
            cls.powershell_exe(),
            "-ExecutionPolicy",
            "Bypass",
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
        return os.path.join(cls.basedir(), cls.name(), "Start-EditorServices.ps1")

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
        return os.path.join(cls.basedir(), cls.name(), "bin", "Common", "Microsoft.PowerShell.EditorServices.dll")

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
        try:
            zipfile = os.path.join(cls.storage_path(), "{}.zip".format(cls.name()))
            urlretrieve(URL.format(cls.version_str()), zipfile)
            with ZipFile(zipfile, "r") as f:
                f.extractall(cls.storage_path())
            os.rename(os.path.join(cls.storage_path(), cls.name()), cls.basedir())
            os.unlink(zipfile)
        except Exception:
            shutil.rmtree(cls.basedir(), ignore_errors=True)
            raise

    def m_powerShell_executionStatusChanged(self, params: Any) -> None:
        pass

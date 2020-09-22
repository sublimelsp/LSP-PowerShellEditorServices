import os
import tempfile

from LSP.plugin import AbstractPlugin
from LSP.plugin.core.typing import Any, Tuple, List
import sublime


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
        return os.path.join(sublime.packages_path(), "LSP-{}".format(cls.name()))

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

    # custom notification handlers

    def m_powerShell_executionStatusChanged(self, params: Any) -> None:
        pass

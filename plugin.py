from __future__ import annotations
import os
import shutil
import subprocess
import tempfile

from typing import Any, Callable
from urllib.request import urlretrieve
from zipfile import ZipFile

import sublime

from LSP.plugin import (
    AbstractPlugin,
    ClientConfig,
    WorkspaceFolder,
    register_plugin,
    unregister_plugin,
)
from LSP.plugin.core.protocol import Location
from LSP.plugin.locationpicker import LocationPicker

URL = "https://github.com/PowerShell/PowerShellEditorServices/releases/download/v{}/PowerShellEditorServices.zip"


class PowerShellEditorServices(AbstractPlugin):
    package_name: str = __spec__.parent
    """
    The real package name on file system.
    """

    # ---- public API methods ----

    @classmethod
    def name(cls) -> str:
        return cls.__name__

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        try:
            powershell_exe = cls.powershell_exe()
            if not powershell_exe:
                # Install only, if powershell is available!
                return False
            cmd = f'[System.Diagnostics.FileVersionInfo]::GetVersionInfo("{cls.dll_path()}").FileVersion'
            version_info = cls.run(powershell_exe, "-NoLogo", "-NoProfile", "-Command", cmd)
            version_info = ".".join(version_info.splitlines()[0].strip().split(".")[0:3])
            return cls.version_str() != version_info
        except Exception:
            pass
        return True

    @classmethod
    def install_or_update(cls) -> None:
        shutil.rmtree(cls.basedir(), ignore_errors=True)
        os.makedirs(cls.storage_path(), exist_ok=True)
        try:
            zipfile = os.path.join(cls.storage_path(), f"{cls.name()}.zip")
            urlretrieve(URL.format(cls.version_str()), zipfile)
            with ZipFile(zipfile, "r") as f:
                f.extractall(cls.basedir())
            os.unlink(zipfile)
        except Exception:
            shutil.rmtree(cls.basedir(), ignore_errors=True)
            raise

    @classmethod
    def can_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: list[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> str | None:
        powershell_exe = cls.powershell_exe()
        if not powershell_exe:
            return f"PowerShell is required to run {cls.name()}!"

        configuration.command = [
            powershell_exe,
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

        return super().can_start(window, initiating_view, workspace_folders, configuration)

    def on_pre_server_command(
        self, command: dict[str, Any], done_callback: Callable[[], None]
    ) -> bool:
        command_name = command["command"]
        if command_name == "editor.action.showReferences":
            _, _, references = command["arguments"]
            self._handle_show_references(references)
            done_callback()
            return True

        if command_name == "PowerShell.ShowCodeActionDocumentation":
            self._handle_show_rule_documentation(command["arguments"][0])
            done_callback()
            return True

        return False

    def m_powerShell_executionStatusChanged(self, params: Any) -> None:
        pass

    # ---- internal methods -----

    @classmethod
    def cleanup(cls):
        try:
            from package_control import events  # type: ignore

            if events.remove(cls.package_name):
                sublime.set_timeout_async(cls.remove_basedir, 1000)
        except ImportError:
            pass  # Package Control is not required.

    @classmethod
    def remove_basedir(cls):
        basedir = cls.basedir()
        # Enable long path support on on Windows
        # to avoid errors when cleaning up paths with more than 256 chars.
        # see: https://stackoverflow.com/a/14076169/4643765
        # see: https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation
        if sublime.platform() == "windows":
            basedir = Rf"\\?\{basedir}"

        shutil.rmtree(basedir, ignore_errors=True)

    @classmethod
    def basedir(cls) -> str:
        return os.path.join(cls.storage_path(), cls.package_name)

    @classmethod
    def start_script(cls) -> str:
        return os.path.join(cls.basedir(), "PowerShellEditorServices", "Start-EditorServices.ps1")

    @classmethod
    def host_version(cls) -> str:
        return f"{sublime.version()}.0.0"

    @classmethod
    def session_details_path(cls) -> str:
        return os.path.join(tempfile.gettempdir(), f"{cls.name()}.json")

    @classmethod
    def log_path(cls) -> str:
        return os.path.join(tempfile.gettempdir(), f"{cls.name()}.log")

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
            "Microsoft.PowerShell.EditorServices.dll",
        )

    @classmethod
    def version_str(cls) -> str:
        settings, _ = cls.configuration()
        return str(settings.get("version"))

    @classmethod
    def powershell_exe(cls) -> str:
        settings, _ = cls.configuration()
        powershell_exe = settings.get("powershell_exe")
        if not powershell_exe or not isinstance(powershell_exe, str):
            powershell_exe = "pwsh"
            if not shutil.which(powershell_exe):
                if sublime.platform() == "windows":
                    powershell_exe = "powershell.exe"
                else:
                    powershell_exe = ""

        return powershell_exe

    @classmethod
    def run(cls, *args: Any, **kwargs: Any) -> str:
        if sublime.platform() == "windows":
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
        else:
            startupinfo = None
        return subprocess.check_output(
            args=args, cwd=kwargs.get("cwd"), startupinfo=startupinfo, timeout=10.0, encoding="utf-8"
        )

    def _handle_show_references(self, references: list[Location]) -> None:
        session = self.weaksession()
        if not session:
            return
        view = sublime.active_window().active_view()
        if not view:
            return
        if len(references) == 1:
            args = {
                "location": references[0],
                "session_name": session.config.name,
            }
            window = view.window()
            if window:
                window.run_command("lsp_open_location", args)
        elif references:
            LocationPicker(view, session, references, side_by_side=False)
        else:
            sublime.status_message("No references found")

    def _handle_show_rule_documentation(self, rule_id: str) -> None:
        if not rule_id:
            return

        if rule_id.startswith("PS"):
            rule_id = rule_id[2:]

        sublime.run_command(
            "open_url",
            {
                "url": "https://docs.microsoft.com/powershell/utility-modules/psscriptanalyzer/rules/"
                + rule_id
            },
        )


def plugin_loaded():
    register_plugin(PowerShellEditorServices)


def plugin_unloaded():
    PowerShellEditorServices.cleanup()
    unregister_plugin(PowerShellEditorServices)

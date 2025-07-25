from __future__ import annotations
import contextlib
import json
import os
import shutil
import tempfile
import time

from io import BytesIO
from typing import Any, Callable
from urllib.request import urlopen, Request as HttpRequest
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


class PowerShellEditorServices(AbstractPlugin):
    package_name: str = __spec__.parent
    """
    The package name on file system.

    Main purpose is to provide python version acnostic package name for use
    in path sensitive locations, to ensure plugin even works if user installs
    package with different name.
    """

    server_version: str = ""
    """
    The language server version to use.
    """

    settings: sublime.Settings
    """
    Package settings
    """

    # ---- public API methods ----

    @classmethod
    def name(cls) -> str:
        return cls.__name__

    @classmethod
    def configuration(cls):
        settings_file_name = f"LSP-{cls.name()}.sublime-settings"
        cls.settings = sublime.load_settings(settings_file_name)
        return cls.settings, f"Packages/{cls.package_name}/{settings_file_name}"

    @classmethod
    def needs_update_or_installation(cls) -> bool:
        server_file = cls.start_script()
        is_upgrade = os.path.isfile(server_file)
        if is_upgrade:
            next_update_check, server_version = cls.load_metadata()
        else:
            next_update_check, server_version = 0, ""

        cls.server_version = str(cls.settings.get("version", "latest"))
        if cls.server_version[0] == "v":
            cls.server_version = cls.server_version[1:]

        if cls.server_version == "latest":
            if int(time.time()) >= next_update_check:
                try:
                    # response url ends with latest available version number
                    request = HttpRequest(url=f"{cls.repo_url()}/releases/latest", method="HEAD")
                    with contextlib.closing(urlopen(request)) as response:
                        available_version = response.url.rstrip("/").rsplit("/", 1)[1]
                        if available_version[0] == "v":
                            available_version = available_version[1:]
                        if available_version != server_version:
                            cls.server_version = available_version
                            return True
                except Exception:
                    cls.save_metadata(False, server_version)

            return False

        return cls.server_version != server_version

    @classmethod
    def install_or_update(cls) -> None:
        cls.remove_server_path()
        os.makedirs(cls.storage_path(), exist_ok=True)

        try:
            with contextlib.closing(urlopen(cls.download_url())) as response:
                with ZipFile(BytesIO(response.read())) as arc:
                    arc.extractall(cls.server_path())
        except Exception:
            cls.remove_server_path()
            raise

        cls.save_metadata(True, cls.server_version)

    @classmethod
    def can_start(
        cls,
        window: sublime.Window,
        initiating_view: sublime.View,
        workspace_folders: list[WorkspaceFolder],
        configuration: ClientConfig,
    ) -> str | None:
        # find powershell executable
        powershell = configuration.settings.get("powershell_exe")
        if not powershell or not isinstance(powershell, str):
            powershell = "pwsh"
            if not shutil.which(powershell):
                if sublime.platform() == "windows":
                    powershell = "powershell.exe"
                else:
                    powershell = ""

        if not powershell:
            return f"PowerShell is required to run {cls.name()}!"

        configuration.command = [
            powershell,
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
            "-LogLevel",
            "Error",
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
                sublime.set_timeout_async(cls.remove_server_path, 1000)
        except ImportError:
            pass  # Package Control is not required.

    @classmethod
    def remove_server_path(cls):
        server_path = cls.server_path()
        # Enable long path support on on Windows
        # to avoid errors when cleaning up paths with more than 256 chars.
        # see: https://stackoverflow.com/a/14076169/4643765
        # see: https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation
        if sublime.platform() == "windows":
            server_path = Rf"\\?\{server_path}"

        shutil.rmtree(server_path, ignore_errors=True)

    @classmethod
    def repo_url(cls) -> str:
        return "https://github.com/PowerShell/PowerShellEditorServices"

    @classmethod
    def download_url(cls) -> str:
        return (
            f"{cls.repo_url()}/releases/download/v{cls.server_version}/PowerShellEditorServices.zip"
        )

    @classmethod
    def server_path(cls) -> str:
        try:
            return cls._server_path
        except AttributeError:
            cls._server_path = os.path.join(cls.storage_path(), cls.package_name)
            return cls._server_path

    @classmethod
    def start_script(cls) -> str:
        return os.path.join(
            cls.server_path(), "PowerShellEditorServices", "Start-EditorServices.ps1"
        )

    @classmethod
    def host_version(cls) -> str:
        return f"{sublime.version()}.0.0"

    @classmethod
    def session_details_path(cls) -> str:
        return os.path.join(tempfile.gettempdir(), f"{cls.name()}.json")

    @classmethod
    def log_path(cls) -> str:
        return os.path.join(cls.server_path(), "logs")

    @classmethod
    def bundled_modules_path(cls) -> str:
        return cls.server_path()

    @classmethod
    def metadata_file(cls) -> str:
        return os.path.join(cls.server_path(), "update.json")

    @classmethod
    def load_metadata(cls) -> tuple[int, str]:
        try:
            with open(cls.metadata_file()) as fobj:
                data = json.load(fobj)
                return int(data["timestamp"]), data["version"]
        except (FileNotFoundError, KeyError, TypeError, ValueError):
            return 0, ""

    @classmethod
    def save_metadata(cls, success: bool, version: str) -> None:
        next_run_delay = (7 * 24 * 60 * 60) if success else (6 * 60 * 60)
        with open(cls.metadata_file(), "w") as fobj:
            json.dump(
                {
                    "timestamp": int(time.time()) + next_run_delay,
                    "version": version,
                },
                fp=fobj,
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
    shutil.rmtree(PowerShellEditorServices.log_path(), ignore_errors=True)
    register_plugin(PowerShellEditorServices)


def plugin_unloaded():
    PowerShellEditorServices.cleanup()
    unregister_plugin(PowerShellEditorServices)

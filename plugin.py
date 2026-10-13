from __future__ import annotations

import contextlib
import json
import os
import shutil
import sublime
import time
from io import BytesIO
from pathlib import Path
from typing import Any, cast, final
from urllib.request import Request as HttpRequest, urlopen
from zipfile import ZipFile

from LSP.plugin import (
    LocationPicker,
    LspPlugin,
    OnPreStartContext,
    PluginStartError,
    Promise,
    command_handler,
    notification_handler,
)
from LSP.protocol import LSPAny, Location


@final
class PowerShellEditorServices(LspPlugin):
    server_version: str = ""
    """
    The language server version to use.
    """

    # ---- public API methods ----

    @classmethod
    def on_pre_start_async(cls, context: OnPreStartContext) -> None:
        configuration = context.configuration
        if cls.needs_update_or_installation(str(configuration.root_settings.get("version", "latest"))):
            cls.install_or_update()

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
            raise PluginStartError(f"PowerShell is required to run {cls.name}!")

        configuration.command = [
            powershell,
            "-NoLogo",
            "-NoProfile",
            "-File",
            str(cls.start_script()),
            "-BundledModulesPath",
            str(cls.plugin_storage_path),
            "-HostName",
            "SublimeText",
            "-HostProfileId",
            "SublimeText",
            "-HostVersion",
            f"{sublime.version()}.0.0",
            "-Stdio",
            "-LogLevel",
            "Error",
            "-LogPath",
            str(cls.log_path()),
            "-SessionDetailsPath",
            str(cls.session_details_file()),
        ]

    @classmethod
    def needs_update_or_installation(cls, version: str) -> bool:
        is_upgrade = cls.start_script().is_file()
        if is_upgrade:
            next_update_check, server_version = cls.load_metadata()
        else:
            next_update_check, server_version = 0, ""

        cls.server_version = version
        if cls.server_version[0] == "v":
            cls.server_version = cls.server_version[1:]

        if cls.server_version == "latest":
            if int(time.time()) >= next_update_check:
                try:
                    available_version = cls.available_version()
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
        os.makedirs(cls.plugin_storage_path.parent, exist_ok=True)

        try:
            with contextlib.closing(urlopen(cls.download_url())) as response:
                with ZipFile(BytesIO(response.read())) as arc:
                    arc.extractall(cls.plugin_storage_path)
        except Exception:
            cls.remove_server_path()
            raise

        cls.save_metadata(True, cls.server_version)

    @command_handler("editor.action.showReferences")
    def on_show_references(self, arguments: list[LSPAny] | None) -> Promise[None]:
        if arguments:
            self._handle_show_references(cast("list[Location]", arguments[2]))
        return Promise.resolve(None)

    @command_handler("PowerShell.ShowCodeActionDocumentation")
    def on_show_code_action_documentation(self, arguments: list[LSPAny] | None) -> Promise[None]:
        if arguments:
            self._handle_show_rule_documentation(cast(str, arguments[0]))
        return Promise.resolve(None)

    @notification_handler("powerShell/executionStatusChanged")
    def on_execution_status_changed(self, params: Any) -> None:
        pass

    # ---- internal methods -----

    @classmethod
    def available_version(cls) -> str:
        # response url ends with latest available version number
        request = HttpRequest(url=f"{cls.repo_url()}/releases/latest", method="HEAD")
        with contextlib.closing(urlopen(request)) as response:
            available_version = response.url.rstrip("/").rsplit("/", 1)[1]
        if available_version[0] == "v":
            available_version = available_version[1:]
        return available_version

    @classmethod
    def cleanup(cls):
        try:
            from package_control import events  # type: ignore

            if events.remove(cls.name):
                sublime.set_timeout_async(cls.remove_server_path, 1000)
        except ImportError:
            pass  # Package Control is not required.

    @classmethod
    def remove_server_path(cls):
        server_path = str(cls.plugin_storage_path)
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
    def start_script(cls) -> Path:
        return cls.plugin_storage_path / "PowerShellEditorServices" / "Start-EditorServices.ps1"

    @classmethod
    def log_path(cls) -> Path:
        return cls.plugin_storage_path / "logs"

    @classmethod
    def session_details_file(cls) -> Path:
        return cls.plugin_storage_path / "session.json"

    @classmethod
    def metadata_file(cls) -> Path:
        return cls.plugin_storage_path / "update.json"

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
    PowerShellEditorServices.register()


def plugin_unloaded():
    PowerShellEditorServices.cleanup()
    PowerShellEditorServices.unregister()

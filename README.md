# LSP-PowerShellEditorServices

Convenience plugin to install and run the [PowerShellEditorServices](https://github.com/PowerShell/PowerShellEditorServices) language server.

To use this package:

1. Install the [LSP](https://packagecontrol.io/packages/LSP)
package
3. Install a Powershell runtime (e.g. you can run `powershell.exe` (Windows) or `pwsh` (macOS/Linux) in your terminal).
2. Install the [PowerShell](https://packagecontrol.io/packages/PowerShell) package for syntax highlighting. Alternatively, you may use Michael Lyons'
[PowerShell syntax rewrite](https://github.com/michaelblyons/PowerShell/tree/sublime-syntax).

This package will download binaries in Sublime Text's `$DATA/Package Storage` directory.

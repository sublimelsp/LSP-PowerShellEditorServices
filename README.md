# LSP-PowerShellEditorServices

Convenience plugin to install and run the [PowerShellEditorServices](https://github.com/PowerShell/PowerShellEditorServices) language server.


## Installation

1. Install a PowerShell runtime
   (e.g. you can run `powershell.exe` (Windows) or `pwsh` (macOS/Linux) in your terminal).

2. Install [PowerShell](https://packagecontrol.io/packages/PowerShell) package for syntax highlighting.  
   Alternatively, you may use Michael Lyons' [PowerShell syntax rewrite](https://github.com/michaelblyons/PowerShell/tree/sublime-syntax).

3. Install [LSP](https://packagecontrol.io/packages/LSP) from Package Control.

4. Install [LSP-PowerShellEditorServices](https://packagecontrol.io/Packages/LSP-PowerShellEditorServices) from Package Control.

> **Note**
>
> The plugin does not distribute but download language server binaries
> 
> - from: https://github.com/PowerShell/PowerShellEditorServices/releases/
> - to: `$DATA/Package Storage`


## Configuration

Open configuration file 
by running `Preferences: LSP-PowerShellEditorServices Settings` from Command Palette 
or via Main Menu (`Preferences > Package Settings > LSP > Servers > LSP-PowerShellEditorServices`).


### Global Script Analysis Settings File

```json
"powershell.scriptAnalysis.settingsPath": "PSScriptAnalyzerSettings.psd1"
```

By default language server looks up script analysis settings in workspace folders, only.

- A given relative path is resolved with workspace folders as root.
- An absolute path can be specified to force usage of a certain settings file.

To provide both a global fallback and project specific files ...

1. specify an absolute path in `LSP-PowerShellEditorServices.sublime-settings`.

   ```json
   {
      "settings":
      {
         "powershell.scriptAnalysis.settingsPath": "${packages}/User/PSScriptAnalyzerSettings.psd1",
      },
   }
   ```

2. specify a relative path in project specific settings via `<My Project>.sublime-project`.

   ```json
   {
      "folders": [
         {
            "path": ".",
         },
      ],
      "settings":
      {
         "LSP":
         {
            "PowerShellEditorServices": {
               "settings": {
                  "powershell.scriptAnalysis.settingsPath": "PSScriptAnalyzerSettings.psd1",
               },
            },
         },
      },
   }
   ```

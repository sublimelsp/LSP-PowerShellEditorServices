#!/usr/bin/env bash
set -e
rm -rf out
rm -rf PowerShellEditorServices
rm -f PowerShellEditorServices.zip
rm -f LSP-PowerShellEditorServices.zip
PWSH_GIT_TAG=${1:-v2.2.0}
echo "PowerShellEditorServices git tag: ${PWSH_GIT_TAG}"
mkdir -p out
cp -R src/* out/
cp LICENSE out/
cp NOTICE out/
touch out/.no-sublime-package
curl -L -s -S >/dev/null https://github.com/PowerShell/PowerShellEditorServices/releases/download/${PWSH_GIT_TAG}/PowerShellEditorServices.zip -o PowerShellEditorServices.zip
unzip -qq PowerShellEditorServices.zip
mv PowerShellEditorServices/* out/
rmdir PowerShellEditorServices
rm PowerShellEditorServices.zip
pushd out
    zip -qq -r LSP-PowerShellEditorServices.zip .
popd
mv out/LSP-PowerShellEditorServices.zip .
rm -rf out

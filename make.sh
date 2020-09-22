#!/usr/bin/env bash
set -e

function set-output
{
    local value="${2//'%'/'%25'}"
    local value="${value//$'\n'/'%0A'}"
    echo "::set-output name=$1::${value//$'\r'/'%0D'}"
}

function main
{
    local pwsh=PowerShellEditorServices
    rm -rf out
    rm -rf $pwsh
    rm -f $pwsh.zip
    rm -f LSP-$pwsh.zip
    mkdir -p out
    cp -R src/* out/
    cp LICENSE out/
    cp NOTICE out/
    touch out/.no-sublime-package
    curl -L -s -S >/dev/null https://github.com/PowerShell/$pwsh/releases/download/$1/$pwsh.zip -o $pwsh.zip
    unzip -qq $pwsh.zip
    mv $pwsh/* out/
    rmdir $pwsh
    rm $pwsh.zip
    pushd out && zip -qq -r LSP-$pwsh.zip . && popd
    mv out/LSP-$pwsh.zip .
    rm -rf out
    set-output artifact LSP-$pwsh.zip
}

main "$@"

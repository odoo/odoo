#!/bin/bash
community=$(cd -- "$(dirname "$0")" &> /dev/null && cd ../../.. && pwd)
tooling="$community/addons/web/tooling"
testRealPath="$(realpath --relative-to=. "$tooling/hooks")"
if [[ $testRealPath == "" ]]; then
    echo "Please install realpath"
    exit 1
fi

refreshInDir () {
    cd "$1" || exit
    cp "$tooling/_eslint.config.mjs" eslint.config.mjs
    cp "$tooling/_jsconfig.json" jsconfig.json
    cp "$tooling/_package.json" package.json
    # Clean up legacy files from ESLint 8
    rm -f .eslintignore .eslintrc.json
    cd - &> /dev/null
}

read -p "Refresh tooling in enterprise ? [y, n]" doEnterprise
if [[ $doEnterprise != "n" ]]; then
    read -p "What is the relative path from community to enterprise ? (../enterprise)" pathToEnterprise
    pathToEnterprise=${pathToEnterprise:-../enterprise}
    pathToEnterprise=$(realpath "$community/$pathToEnterprise")
fi

refreshInDir "$community"

if [[ $doEnterprise != "n" ]]
then
    refreshInDir "$pathToEnterprise" copy
fi

echo ""
echo "The JS tooling config files have been refreshed"
echo "Make sure to refresh the eslint and typescript service and configure your IDE so it uses the config files"
echo 'For VSCode, look inside your .vscode/settings.json file ("editor.defaultFormatter": "dbaeumer.vscode-eslint")'
echo "If you still have issues, try doing a full reload instead which will reinstall the node modules"
echo ""

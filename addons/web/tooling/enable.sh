#!/bin/bash

script="$0"
basename="$(dirname "$script")"

read -p "Do you want the tooling installed in enterprise too ? [y, n]" willingToInstallToolingInEnterprise
if [[ $willingToInstallToolingInEnterprise != "n" ]]
then
    read -p "What is the relative path from community to enterprise ? (../enterprise)" pathToEnterprise
    pathToEnterprise=${pathToEnterprise:-../enterprise}
fi

cp -r "$basename/_husky"  "$basename/../../../.husky"
cp  "$basename/_eslintignore"  "$basename/../../../.eslintignore"
cp  "$basename/_prettierignore"  "$basename/../../../.prettierignore"
cp  "$basename/_eslintrc.json"  "$basename/../../../.eslintrc.json"
cp  "$basename/_prettierrc.json"  "$basename/../../../.prettierrc.json"
cp  "$basename/_package.json"  "$basename/../../../package.json"

if [[ $willingToInstallToolingInEnterprise != "n" ]]
then
    cp -r "$basename/_husky"  "$basename/../../../$pathToEnterprise/.husky"
    cp  "$basename/_eslintignore"  "$basename/../../../$pathToEnterprise/.eslintignore"
    cp  "$basename/_prettierignore"  "$basename/../../../$pathToEnterprise/.prettierignore"
    cp  "$basename/_eslintrc.json"  "$basename/../../../$pathToEnterprise/.eslintrc.json"
    cp  "$basename/_prettierrc.json"  "$basename/../../../$pathToEnterprise/.prettierrc.json"
    cp  "$basename/_package.json" "$basename/../../../$pathToEnterprise/package.json"
fi

cd "$basename"
npm install
cd -

if [[ $willingToInstallToolingInEnterprise != "n" ]]
then
    cd "$basename/../../../$pathToEnterprise"
    npm install
    cd -
fi

echo ""
echo "JS tooling have been added to the roots"
echo "Make sure to refresh the eslint service and configure your IDE so it uses the config files"
echo 'For VSCode, look inside your .vscode/settings.json file ("editor.defaultFormatter": "dbaeumer.vscode-eslint")'
echo ""

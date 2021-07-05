#!/bin/bash

script="$0"
basename="$(dirname "$script")"

read -p "Do you want to delete the tooling installed in enterprise too ? [y, n]" willingToDeleteToolingInEnterprise
if [[ $willingToDeleteToolingInEnterprise != "n" ]]
then
    read -p "What is the relative path from community to enterprise ? (../enterprise)" pathToEnterprise
    pathToEnterprise=${pathToEnterprise:-../enterprise}
fi

rm -rf "$basename/../../../.husky"
rm -rf "$basename/../../../.eslintignore"
rm -rf "$basename/../../../.prettierignore"
rm -rf "$basename/../../../.eslintrc.json"
rm -rf "$basename/../../../.prettierrc.json"
rm -rf "$basename/../../../package.json"
rm -rf "$basename/../../../package-lock.json"
rm -rf "$basename/../../../node_modules"

if [[ $willingToDeleteToolingInEnterprise != "n" ]]
then
    rm -rf "$basename/../../../$pathToEnterprise/.husky"
    rm -rf "$basename/../../../$pathToEnterprise/.eslintignore"
    rm -rf "$basename/../../../$pathToEnterprise/.prettierignore"
    rm -rf "$basename/../../../$pathToEnterprise/.eslintrc.json"
    rm -rf "$basename/../../../$pathToEnterprise/.prettierrc.json"
    rm -rf "$basename/../../../$pathToEnterprise/package.json"
    rm -rf "$basename/../../../$pathToEnterprise/package-lock.json"
    rm -rf "$basename/../../../$pathToEnterprise/node_modules"
fi


echo ""
echo "JS tooling have been removed from the roots"
echo ""

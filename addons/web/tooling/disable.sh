#!/bin/bash
community=$(cd -- "$(dirname "$0")" &> /dev/null && cd ../../.. && pwd)

disableInDir () {
    cd "$1" || exit
    git config --unset core.hooksPath
    rm .eslintignore
    rm .eslintrc.json
    rm jsconfig.json
    rm package.json
    rm package-lock.json
    rm -r node_modules
    cd - &> /dev/null
}

read -p "Do you want to delete the tooling installed in enterprise too ? [y, n]" willingToDeleteToolingInEnterprise
if [[ $willingToDeleteToolingInEnterprise != "n" ]]
then
    read -p "What is the relative path from community to enterprise ? (../enterprise)" pathToEnterprise
    pathToEnterprise=${pathToEnterprise:-../enterprise}
    pathToEnterprise=$(realpath "$community/$pathToEnterprise")
fi

disableInDir "$community"

if [[ $willingToDeleteToolingInEnterprise != "n" ]]
then
    disableInDir "$pathToEnterprise"
fi


echo ""
echo "JS tooling have been removed from the roots"
echo ""

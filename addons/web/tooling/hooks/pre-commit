#!/bin/bash
tooling_dir=$(cd -- "$(dirname "$0")" &> /dev/null && cd .. && pwd)
if ! cmp -s -- "$tooling_dir/_package.json" package.json; then
    echo "Your package.json is out of date, reloading the tooling using the reload script"
    "$tooling_dir/reload.sh"
elif
    ! cmp -s -- "$tooling_dir/_eslintignore" .eslintignore ||
    ! cmp -s -- "$tooling_dir/_eslintrc.json" .eslintrc.json
then
    echo "Some of your eslint/prettier config files are out of date, refreshing them using the refresh script"
    "$tooling_dir/refresh.sh"
fi
npm run format-staged

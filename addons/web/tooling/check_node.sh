#!/bin/bash
tooling_dir=$(cd -- "$(dirname "$0")" &> /dev/null && pwd)
required=$(sed -n 's/^ *"node": "\(.*\)"$/\1/p' "$tooling_dir/_package.json")

if ! command -v node &> /dev/null; then
    echo "The JS tooling needs Node.js $required, which is not installed: the JS and CSS files are not linted."
    exit 1
fi

if ! node -e '
    const have = process.versions.node.split(".").map(Number);
    const ok = process.argv[1].split("||").some((range) => {
        const [, operator, ...version] = range.trim().match(/^(\^|>=)(\d+)(?:\.(\d+))?(?:\.(\d+))?$/);
        const want = version.map((part) => Number(part || 0));
        const cmp = have[0] - want[0] || have[1] - want[1] || have[2] - want[2];
        return cmp >= 0 && (operator === ">=" || have[0] === want[0]);
    });
    process.exit(ok ? 0 : 1);
' "$required"; then
    echo "The JS tooling needs Node.js $required, you have $(node --version): the JS and CSS files are not linted."
    echo "Upgrade Node.js (e.g. with nvm), then run addons/web/tooling/reload.sh"
    exit 1
fi

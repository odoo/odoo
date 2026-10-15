#!/bin/bash
if ! command -v node &> /dev/null; then
    echo "The JS tooling needs Node.js, which is not installed: the JS and CSS files are not linted."
    exit 1
fi
node "$(dirname "$0")/check_node.cjs"

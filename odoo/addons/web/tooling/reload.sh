#!/bin/bash
community=$(cd -- "$(dirname "$0")" &> /dev/null && cd ../../.. && pwd)

"$community/addons/web/tooling/disable.sh"
"$community/addons/web/tooling/enable.sh"

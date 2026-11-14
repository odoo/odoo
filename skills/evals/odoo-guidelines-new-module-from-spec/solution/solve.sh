#!/bin/bash
# Oracle: put back the printer module (translations aside) and what
# stock_delivery built on it, then commit.
set -euo pipefail
cd /app
cp -R /solution/printer addons/printer
git apply /solution/stock_delivery.patch
git add -A
git commit -q -m "[IMP] stock_delivery: native epos/zpl automatic printing" \
    -m "Print shipping labels and other reports on Epson ePOS and Zebra ZPL network printers, from the browser, without an IoT box."

#!/bin/sh
set -e
ABI=$(rpm -q --provides python3 | uniq | awk '/abi/ {print $NF}')
python3 setup.py install --prefix=/usr --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES --install-lib usr/lib/python${ABI}/site-packages/

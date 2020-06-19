#!/bin/sh
set -e
python3 setup.py install --prefix=/usr --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES --install-lib usr/lib/python3.7/site-packages/

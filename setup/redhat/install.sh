#!/bin/sh
set -e
python setup.py install --prefix=/usr --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

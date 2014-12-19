#!/bin/sh
set -e
python2.6 setup.py install --prefix=/usr --root=$RPM_BUILD_ROOT --record=INSTALLED_FILES

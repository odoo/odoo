#!/bin/bash

# Create NorTK odoo ERP distribution

set -eux
SOURCE_PATH="../../.."
VERSION=$(grep -Po 'version_info = \(\K.*,.*,.*(?=, .*, .*, .*\))' $SOURCE_PATH/odoo/release.py | sed 's/, /\./g')
SOURCES="${RPM_BUILD_DIR}/SOURCES/odoo-${VERSION}.tar.gz"

echo "Packaging sources"
tar --exclude '.git' --exclude '.github'            \
    --transform "s/^\\./odoo-${VERSION}/" -c -z -f  \
    ${SOURCES} .



#!/bin/bash

# Prepare and build NorTK odoo RPM distribution

set -eux
SOURCE_PATH="../../.."
#RPM_BUILD_DIR="$(pwd)/rpmbuild"
RPM_BUILD_DIR="${HOME}/rpmbuild"

VERSION=$(grep -Po 'version_info = \(\K.*,.*,.*(?=, .*, .*, .*\))' $SOURCE_PATH/odoo/release.py | sed 's/, /\./g')
TSTAMP=$(date '+%d%m%Y')
BUILD_DATE=$(LANG=C date '+%a %b %d %Y')
SOURCES="${RPM_BUILD_DIR}/SOURCES/odoo-${VERSION}.tar.gz"
SPEC_FILE=${RPM_BUILD_DIR}/SPECS/odoo.spec

rpmdev-setuptree -d
cp odoo.spec ${RPM_BUILD_DIR}/SPECS/

pushd $SOURCE_PATH
mkdir -p dist

if [[ ! -f $SOURCES ]]; then
    echo "Packaging sources"
    tar --exclude '.git' --exclude '.github'            \
        --transform "s/^\\./odoo-${VERSION}/" -c -z -f  \
        ${SOURCES} .
else
    echo "Sources already packed, skipping"
fi

#spectool -gaR                            \
#    --define "version ${VERSION}"       \
#    --define "release ${TSTAMP}"        \
#    --define "build_date ${BUILD_DATE}" \
#    $SPEC_FILE

echo "Installing dependencies"
sudo dnf -y builddep                    \
    --define "version ${VERSION}"       \
    --define "release ${TSTAMP}"        \
    --define "build_date ${BUILD_DATE}" \
    $SPEC_FILE


echo "Building RPM"
rpmbuild -ba                             \
    --define "%version ${VERSION}"       \
    --define "%release ${TSTAMP}"        \
    --define "%build_date ${BUILD_DATE}" \
    ${SPEC_FILE}

#mv {rpmbuild_dir}/RPMS/noarch/odoo*.rpm /data/src/dist/

popd

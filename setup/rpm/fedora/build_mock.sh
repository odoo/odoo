#!/bin/bash

# Prepare and build NorTK odoo RPM distribution

set -eux
SOURCE_PATH="../../.."
#RPM_BUILD_DIR="$(pwd)/rpmbuild"
RPM_BUILD_DIR="${HOME}/rpmbuild"

VERSION=$(grep -Po 'version_info = \(\K.*,.*,.*(?=, .*, .*, .*\))' $SOURCE_PATH/odoo/release.py | sed 's/, /\./g')
TAG=$(git rev-parse --abbrev-ref HEAD)
TSTAMP=$(date '+%Y%m%d')
BUILD_DATE=$(LANG=C date '+%a %b %d %Y')
SOURCES="${RPM_BUILD_DIR}/SOURCES/odoo-${TAG}.tar.gz"
SPEC_FILE=${RPM_BUILD_DIR}/SPECS/odoo-devel.spec

rpmdev-setuptree -d
cp *.spec ${RPM_BUILD_DIR}/SPECS/

pushd $SOURCE_PATH
mkdir -p dist

if [[ ! -f $SOURCES ]]; then
    echo "Packaging sources"
    tar --exclude '.git' --exclude '.github'            \
        --transform "s/^\\./odoo-${TAG}/" -c -z -f  \
        ${SOURCES} .
else
    echo "Sources already packed, skipping"
fi

#spectool -gaR                            \
#    --define "version ${VERSION}"       \
#    --define "release ${TSTAMP}"        \
#    --define "build_date ${BUILD_DATE}" \
#    $SPEC_FILE

#echo "Installing dependencies"
#sudo dnf -y builddep                    \
#    $SPEC_FILE


echo "Building Source RPM"
output=$(LANG=C rpmbuild -bs        \
    --define "ts ${TSTAMP}"        \
    ${SPEC_FILE})

package=$( echo $output | grep -Po '(?<=Wrote: ).+.src.rpm' )

# Build RPM
mock -r fedora-43-x86_64         \
    --chain                      \
    --define "%ts ${TSTAMP}"     \
    --localrepo=$HOME/rpmbuild/  \
    ${package}

popd

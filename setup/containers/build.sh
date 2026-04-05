#!/bin/bash

# Create a container image for NorTK Odoo
#

VERSION="latest"

if [[ ${1} == "" || ! -f ${1} ]]; then
    echo "Missing Odoo RPM package"
    exit
fi

RPM=$1

echo "Creating NorTK Odoo container image"
cp $RPM odoo.rpm
podman build -t odoo-nortk:${VERSION} -f Containerfile.fedora

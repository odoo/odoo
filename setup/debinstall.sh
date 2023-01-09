#!/bin/sh
#
# Install Debian packages needed to run Odoo.

if [ "$(id -u)" -ne "0" ]; then
   echo "This script must be run as root" >&2
   exit 1
fi

script_path=$(realpath "$0")
script_dir=$(dirname "$script_path")
control_path=$(realpath "$script_dir/../debian/control")

apt-get update
sed -n '/^Depends:/,/^[A-Z]/p' "$control_path" \
| awk '/^ [a-z]/ { gsub(/,/,"") ; print $1 }' | sort -u \
| DEBIAN_FRONTEND=noninteractive xargs apt-get install -y -qq

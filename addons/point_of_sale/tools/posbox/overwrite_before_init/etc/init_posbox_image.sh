#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__file="${__dir}/$(basename "${BASH_SOURCE[0]}")"
__base="$(basename ${__file} .sh)"

# Recommends: antiword, graphviz, ghostscript, postgresql, python-gevent, poppler-utils
export DEBIAN_FRONTEND=noninteractive

mount /dev/sda1 /boot

apt-get update
apt-get -y dist-upgrade

PKGS_TO_INSTALL="adduser postgresql-client python python-dateutil python-decorator python-docutils python-feedparser python-imaging python-jinja2 python-ldap python-libxslt1 python-lxml python-mako python-mock python-openid python-passlib python-psutil python-psycopg2 python-pybabel python-pychart python-pydot python-pyparsing python-pypdf python-reportlab python-requests python-tz python-vatnumber python-vobject python-werkzeug python-xlwt python-yaml postgresql python-gevent python-serial python-pip python-dev localepurge vim mc mg screen iw hostapd isc-dhcp-server git rsync console-data"

apt-get -y install ${PKGS_TO_INSTALL}

apt-get clean
localepurge
rm -rf /usr/share/doc

# python-usb in wheezy is too old
# the latest pyusb from pip does not work either, usb.core.find() never returns
# this may be fixed with libusb>2:1.0.11-1, but that's the most recent one in raspbian
# so we install the latest pyusb that works with this libusb
pip install pyusb==1.0.0b1
pip install qrcode
pip install evdev

groupadd usbusers
usermod -a -G usbusers pi
usermod -a -G lp pi

sudo -u postgres createuser -s pi
mkdir /var/log/odoo
chown pi:pi /var/log/odoo

# logrotate is very picky when it comes to file permissions
chown -R root:root /etc/logrotate.d/
chmod -R 644 /etc/logrotate.d/
chown root:root /etc/logrotate.conf
chmod 644 /etc/logrotate.conf

echo "* * * * * rm /var/run/odoo/sessions/*" | crontab -

update-rc.d -f hostapd remove
update-rc.d -f isc-dhcp-server remove

systemctl daemon-reload
systemctl enable ramdisks.service
systemctl disable dphys-swapfile.service

# https://www.raspberrypi.org/forums/viewtopic.php?p=79249
# to not have "setting up console font and keymap" during boot take ages
setupcon

# create dirs for ramdisks
create_ramdisk_dir () {
    mkdir "${1}_ram"
}

create_ramdisk_dir "/var"
create_ramdisk_dir "/etc"
create_ramdisk_dir "/tmp"
mkdir /root_bypass_ramdisks

reboot

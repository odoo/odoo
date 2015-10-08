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

# GUI-related packages
PKGS_TO_DELETE="xserver-xorg-video-fbdev xserver-xorg xinit gstreamer1.0-x gstreamer1.0-omx gstreamer1.0-plugins-base gstreamer1.0-plugins-good gstreamer1.0-plugins-bad gstreamer1.0-alsa gstreamer1.0-libav epiphany-browser lxde lxtask menu-xdg gksu xserver-xorg-video-fbturbo xpdf gtk2-engines alsa-utils netsurf-gtk zenity desktop-base lxpolkit weston omxplayer raspberrypi-artwork lightdm gnome-themes-standard-data gnome-icon-theme qt50-snapshot qt50-quick-particle-examples idle python-pygame python-tk idle3 python-serial python-picamera debian-reference-en dillo x2x scratch nuscratch raspberrypi-ui-mods timidity smartsim penguinspuzzle pistore sonic-pi python-pifacecommon python-pifacedigitalio oracle-java8-jdk minecraft-pi python-minecraftpi wolfram-engine raspi-config libgl1-mesa-dri libicu48 pypy-upstream lxde-icon-theme python3 avahi-daemon"
INSTALLED_PKGS_TO_DELETE=""
set +o errexit
for CURRENT_PKG in $(echo $PKGS_TO_DELETE); do
  $(dpkg --status $CURRENT_PKG &> /dev/null)
  if [[ $? -eq 0 ]]; then
    INSTALLED_PKGS_TO_DELETE="$INSTALLED_PKGS_TO_DELETE $CURRENT_PKG"
  fi
done
set -o errexit

apt-get -y remove --purge ${INSTALLED_PKGS_TO_DELETE}

# Remove automatically installed dependency packages
apt-get -y autoremove

apt-get update
apt-get -y dist-upgrade

PKGS_TO_INSTALL="adduser postgresql-client python python-dateutil python-decorator python-docutils python-feedparser python-imaging python-jinja2 python-ldap python-libxslt1 python-lxml python-mako python-mock python-openid python-passlib python-psutil python-psycopg2 python-pybabel python-pychart python-pydot python-pyparsing python-pypdf python-reportlab python-requests python-simplejson python-tz python-unittest2 python-vatnumber python-vobject python-werkzeug python-xlwt python-yaml postgresql python-gevent python-serial python-pip python-dev localepurge vim mc mg screen iw hostapd isc-dhcp-server"

apt-get -y install ${PKGS_TO_INSTALL}

apt-get clean
localepurge
rm -rf /usr/share/doc
rm -rf /home/pi/python_games

# remove raspi-config notice, it's not necessary and it's not installed anyway
rm -f /etc/profile.d/raspi-config.sh

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

# https://www.raspberrypi.org/forums/viewtopic.php?p=79249
# to not have "setting up console font and keymap" during boot take ages
setupcon

# create dirs for ramdisks
create_ramdisk_dir () {
    mkdir "${1}_ram"
}

create_ramdisk_dir "/var"
create_ramdisk_dir "/etc"
mkdir /root_bypass_ramdisks

reboot

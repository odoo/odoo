#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__file="${__dir}/$(basename "${BASH_SOURCE[0]}")"
__base="$(basename ${__file} .sh)"

# Since we are emulating, the real /boot is not mounted, 
# leading to mismatch between kernel image and modules.
mount /dev/sda1 /boot

# Recommends: antiword, graphviz, ghostscript, postgresql, python-gevent, poppler-utils
export DEBIAN_FRONTEND=noninteractive
echo "nameserver 8.8.8.8" >> /etc/resolv.conf


apt-get update && apt-get -y upgrade
# Do not be too fast to upgrade to more recent firmware and kernel than 4.38
# Firmware 4.44 seems to prevent the LED mechanism from working

PKGS_TO_INSTALL="
    fswebcam \
    nginx-full \
    dnsmasq \
    cups \
    printer-driver-all \
    cups-ipp-utils \
    localepurge \
    vim \
    mc \
    mg \
    screen \
    iw \
    hostapd \
    git \
    rsync \
    console-data \
    lightdm \
    xserver-xorg-video-fbdev \
    xserver-xorg-input-evdev \
    iceweasel \
    xdotool \
    unclutter \
    x11-utils \
    openbox \
    rpi-update \
    adduser \
    postgresql \
    python3 \
    python3-urllib3 \
    python3-dateutil \
    python3-decorator \
    python3-docutils \
    python3-feedparser \
    python3-pil \
    python3-jinja2 \
    python3-ldap3 \
    python3-lxml \
    python3-mako \
    python3-mock \
    python3-openid \
    python3-psutil \
    python3-psycopg2 \
    python3-babel \
    python3-pydot \
    python3-pyparsing \
    python3-pypdf2 \
    python3-reportlab \
    python3-requests \
    python3-simplejson \
    python3-tz \
    python3-vatnumber \
    python3-werkzeug \
    python3-serial \
    python3-pip \
    python3-dev \
    python3-netifaces \
    python3-passlib \
    python3-libsass \
    python3-qrcode \
    python3-html2text \
    python3-unittest2 \
    python3-simplejson"

echo "Acquire::Retries "16";" > /etc/apt/apt.conf.d/99acquire-retries
# KEEP OWN CONFIG FILES DURING PACKAGE CONFIGURATION
# http://serverfault.com/questions/259226/automatically-keep-current-version-of-config-files-when-apt-get-install
apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install ${PKGS_TO_INSTALL}
pg_lsclusters
systemctl start postgresql@9.6-main
systemctl status postgresql@9.6-main

sudo -u postgres createuser -s pi

apt-get clean
localepurge
rm -rf /usr/share/doc

# python-usb in wheezy is too old
# the latest pyusb from pip does not work either, usb.core.find() never returns
# this may be fixed with libusb>2:1.0.11-1, but that's the most recent one in raspbian
# so we install the latest pyusb that works with this libusb.
# Even in stretch, we had an error with langid (but worked otherwise)
pip3 install pyusb==1.0.0b1
pip3 install evdev
pip3 install gatt


groupadd usbusers
usermod -a -G usbusers pi
usermod -a -G lp pi
usermod -a -G input lightdm
mkdir /var/log/odoo
chown pi:pi /var/log/odoo
chown pi:pi -R /home/pi/odoo/

# logrotate is very picky when it comes to file permissions
chown -R root:root /etc/logrotate.d/
chmod -R 644 /etc/logrotate.d/
chown root:root /etc/logrotate.conf
chmod 644 /etc/logrotate.conf

echo "* * * * * rm /var/run/odoo/sessions/*" | crontab -

update-rc.d -f hostapd remove
update-rc.d -f nginx remove
update-rc.d -f dnsmasq remove

systemctl daemon-reload
systemctl enable ramdisks.service
systemctl disable dphys-swapfile.service
systemctl enable ssh

# USER PI AUTO LOGIN (from nano raspi-config)
# We take the whole algorithm from raspi-config in order to stay compatible with raspbian infrastructure
if command -v systemctl > /dev/null && systemctl | grep -q '\-\.mount'; then
        SYSTEMD=1
elif [ -f /etc/init.d/cron ] && [ ! -h /etc/init.d/cron ]; then
        SYSTEMD=0
else
        echo "Unrecognised init system"
        return 1
fi
if [ $SYSTEMD -eq 1 ]; then
    systemctl set-default graphical.target
    ln -fs /etc/systemd/system/autologin@.service /etc/systemd/system/getty.target.wants/getty@tty1.service
    rm /etc/systemd/system/sysinit.target.wants/systemd-timesyncd.service
else
    update-rc.d lightdm enable 2
fi

# disable overscan in /boot/config.txt, we can't use
# overwrite_after_init because it's on a different device
# (/dev/mmcblk0p1) and we don't mount that afterwards.
# This option disables any black strips around the screen
# cf: https://www.raspberrypi.org/documentation/configuration/raspi-config.md
echo "disable_overscan=1" >> /boot/config.txt

# https://www.raspberrypi.org/forums/viewtopic.php?p=79249
# to not have "setting up console font and keymap" during boot take ages
setupcon

# exclude /drivers folder from git info to be able to load specific drivers
mkdir /home/pi/odoo/addons/hw_drivers/drivers/
chmod 777 /home/pi/odoo/addons/hw_drivers/drivers/
echo "addons/hw_drivers/drivers/" > /home/pi/odoo/.git/info/exclude

# create dirs for ramdisks
create_ramdisk_dir () {
    mkdir "${1}_ram"
}

create_ramdisk_dir "/var"
create_ramdisk_dir "/etc"
create_ramdisk_dir "/tmp"
mkdir /root_bypass_ramdisks
umount /dev/sda1

reboot

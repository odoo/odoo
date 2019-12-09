#!/usr/bin/env bash
set -o errexit
set -o nounset
set -o pipefail
# set -o xtrace

__dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
__file="${__dir}/$(basename "${BASH_SOURCE[0]}")"
__base="$(basename ${__file} .sh)"

# Recommends: antiword, graphviz, ghostscript, python-gevent, poppler-utils
export DEBIAN_FRONTEND=noninteractive
echo "nameserver 8.8.8.8" >> /etc/resolv.conf

# set locale to en_US
echo "set locale to en_US"
echo "export LANGUAGE=en_US.UTF-8" >> ~/.bashrc
echo "export LANG=en_US.UTF-8" >> ~/.bashrc
echo "export LC_ALL=en_US.UTF-8" >> ~/.bashrc
locale-gen
source ~/.bashrc

apt-get update && apt-get -y upgrade
# Do not be too fast to upgrade to more recent firmware and kernel than 4.38
# Firmware 4.44 seems to prevent the LED mechanism from working

PKGS_TO_INSTALL="
    fswebcam \
    nginx-full \
    dnsmasq \
    dbus \
    dbus-x11 \
    cups \
    printer-driver-all \
    cups-ipp-utils \
    libcups2-dev \
    pcscd \
    localepurge \
    vim \
    mc \
    mg \
    screen \
    iw \
    hostapd \
    git \
    rsync \
    swig \
    console-data \
    lightdm \
    xserver-xorg-video-fbdev \
    xserver-xorg-input-evdev \
    firefox-esr \
    xdotool \
    unclutter \
    x11-utils \
    xserver-xorg-video-dummy \
    openbox \
    rpi-update \
    adduser \
    libpq-dev \
    python-cups \
    python3 \
    python3-pyscard \
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

apt-get clean
localepurge
rm -rf /usr/share/doc

# python-usb in wheezy is too old
# the latest pyusb from pip does not work either, usb.core.find() never returns
# this may be fixed with libusb>2:1.0.11-1, but that's the most recent one in raspbian
# so we install the latest pyusb that works with this libusb.
# Even in stretch, we had an error with langid (but worked otherwise)
PIP_TO_INSTALL="
    pyusb==1.0.0b1 \
    evdev \
    gatt \
    v4l2 \
    polib \
    pycups"

pip3 install ${PIP_TO_INSTALL}

# Dowload MPD server and library for Six terminals
wget 'https://nightly.odoo.com/master/iotbox/eftdvs' -P /usr/local/bin/
chmod +x /usr/local/bin/eftdvs
wget 'https://nightly.odoo.com/master/iotbox/eftapi.so' -P /usr/lib/

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
update-rc.d timesyncd defaults

systemctl enable ramdisks.service
systemctl disable dphys-swapfile.service
systemctl enable ssh
systemctl set-default graphical.target
systemctl disable getty@tty1.service
systemctl enable autologin@.service
systemctl disable systemd-timesyncd.service
systemctl unmask hostapd.service
systemctl disable hostapd.service

# disable overscan in /boot/config.txt, we can't use
# overwrite_after_init because it's on a different device
# (/dev/mmcblk0p1) and we don't mount that afterwards.
# This option disables any black strips around the screen
# cf: https://www.raspberrypi.org/documentation/configuration/raspi-config.md
echo "disable_overscan=1" >> /boot/config.txt

# Separate framebuffers for both screens on RPI4
sed -i '/dtoverlay/d' /boot/config.txt

# exclude /drivers folder from git info to be able to load specific drivers
echo "addons/hw_drivers/drivers/" > /home/pi/odoo/.git/info/exclude

# create dirs for ramdisks
create_ramdisk_dir () {
    mkdir "${1}_ram"
}

create_ramdisk_dir "/var"
create_ramdisk_dir "/etc"
create_ramdisk_dir "/tmp"
mkdir /root_bypass_ramdisks

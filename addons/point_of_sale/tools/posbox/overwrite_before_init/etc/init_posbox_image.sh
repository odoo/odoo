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

# set locale to en_US
echo "set locale to en_US"
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
locale-gen
# Environment variables
echo "export LANGUAGE=en_US.UTF-8" >> ~/.bashrc
echo "export LANG=en_US.UTF-8" >> ~/.bashrc
echo "export LC_ALL=en_US.UTF-8" >> ~/.bashrc
echo "export DISPLAY=:0" | tee -a ~/.bashrc /home/pi/.bashrc
echo "export XAUTHORITY=/run/lightdm/pi/xauthority" >> /home/pi/.bashrc
echo "export XAUTHORITY=/run/lightdm/root/:0" >> ~/.bashrc
# Aliases
echo  "alias ll='ls -al'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo='sudo systemctl stop odoo; /usr/bin/python3 /home/pi/odoo/odoo-bin --config /home/pi/odoo.conf --load=hw_drivers,hw_escpos,hw_posbox_homepage,point_of_sale,web'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo_logs='less +F /var/log/odoo/odoo-server.log'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias write_mode='sudo mount -o remount,rw / && sudo mount -o remount,rw /root_bypass_ramdisks'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo_conf='cat /home/pi/odoo.conf'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias read_mode='sudo mount -o remount,ro / && sudo mount -o remount,ro /root_bypass_ramdisks'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias install='sudo mount -o remount,rw / && sudo mount -o remount,rw /root_bypass_ramdisks && sudo chroot /root_bypass_ramdisks/'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias blackbox='ls /dev/serial/by-path/'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias nano='write_mode; nano -l'" | tee -a /home/pi/.bashrc
echo  "alias vim='write_mode; sudo vim'" | tee -a /home/pi/.bashrc
echo  "alias odoo_luxe='printf \" ______\n< Luxe >\n ------\n        \\   ^__^\n         \\  (oo)\\_______\n            (__)\\       )\\/\\ \n                ||----w |\n                ||     ||\n\"'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo_start='sudo systemctl start odoo'" >> /home/pi/.bashrc
echo  "alias odoo_stop='sudo systemctl stop odoo'" >> /home/pi/.bashrc
echo  "alias odoo_restart='sudo systemctl restart odoo'" >> /home/pi/.bashrc
echo "
odoo_help() {
  echo 'Welcome to Odoo IoTBox tools'
  echo 'odoo                Starts/Restarts Odoo server manually (not through odoo.service)'
  echo 'odoo_logs           Displays Odoo server logs in real time'
  echo 'odoo_conf           Displays Odoo configuration file content'
  echo 'write_mode          Enables system write mode'
  echo 'read_mode           Switches system to read-only mode'
  echo 'install             Bypasses ramdisks to allow package installation'
  echo 'blackbox            Lists all serial connected devices'
  echo 'odoo_start          Starts Odoo service'
  echo 'odoo_stop           Stops Odoo service'
  echo 'odoo_restart        Restarts Odoo service'
  echo 'odoo_dev <branch>   Resets Odoo on the specified branch from odoo-dev repository'
}

odoo_dev() {
  if [ -z \"\$1\" ]; then
    odoo_help
    return
  fi
  write_mode
  pwd=\$(pwd)
  cd /home/pi/odoo
  git remote add dev https://github.com/odoo-dev/odoo.git
  git fetch dev \$1 --depth=1 --prune
  git reset --hard dev/\$1
  cd \$pwd
}

pip() {
  if [[ -z \"\$1\" || -z \"\$2\" ]]; then
    odoo_help
    return 1
  fi
  additional_arg=\"\"
  if [ \"\$1\" == \"install\" ]; then
    additional_arg=\"--user\"
  fi
  pip3 \"\$1\" \"\$2\" --break-system-package \$additional_arg
}
" | tee -a ~/.bashrc /home/pi/.bashrc

source ~/.bashrc
source /home/pi/.bashrc

# copy the odoo.conf file to the overwrite directory
mv -v "/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/odoo.conf" "/home/pi/"
chown pi:pi "/home/pi/odoo.conf"

apt-get update

# At the first start it is necessary to configure a password
# This will be modified by a unique password on the first start of Odoo
password="$(openssl rand -base64 12)"
echo "pi:${password}" | chpasswd

echo "Acquire::Retries "16";" > /etc/apt/apt.conf.d/99acquire-retries
# KEEP OWN CONFIG FILES DURING PACKAGE CONFIGURATION
# http://serverfault.com/questions/259226/automatically-keep-current-version-of-config-files-when-apt-get-install
xargs apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install < /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/packages.txt
apt-get -y autoremove

apt-get clean
localepurge
rm -rfv /usr/share/doc

pip3 install -r /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/requirements.txt --break-system-package

# Dowload MPD server and library for Six terminals
wget 'https://nightly.odoo.com/master/iotbox/eftdvs' -P /usr/local/bin/
chmod +x /usr/local/bin/eftdvs
wget 'https://nightly.odoo.com/master/iotbox/eftapi.so' -P /usr/lib/

groupadd usbusers
usermod -a -G usbusers pi
usermod -a -G lp pi
usermod -a -G input lightdm
mkdir -v /var/log/odoo
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

systemctl enable ramdisks.service
systemctl enable led-status.service
systemctl disable dphys-swapfile.service
systemctl enable ssh
systemctl set-default graphical.target
systemctl disable getty@tty1.service
systemctl enable systemd-timesyncd.service
systemctl unmask hostapd.service
systemctl disable hostapd.service
systemctl disable cups-browsed.service
systemctl enable odoo.service

# disable overscan in /boot/config.txt, we can't use
# overwrite_after_init because it's on a different device
# (/dev/mmcblk0p1) and we don't mount that afterwards.
# This option disables any black strips around the screen
# cf: https://www.raspberrypi.org/documentation/configuration/raspi-config.md
echo "disable_overscan=1" >> /boot/config.txt

# Use the fkms driver instead of the legacy one (RPI3 requires this)
sed -i '/dtoverlay/c\dtoverlay=vc4-fkms-v3d' /boot/config.txt

# exclude /drivers folder from git info to be able to load specific drivers
echo "addons/hw_drivers/iot_devices/" > /home/pi/odoo/.git/info/exclude

# create dirs for ramdisks
create_ramdisk_dir () {
    mkdir -v "${1}_ram"
}

create_ramdisk_dir "/var"
create_ramdisk_dir "/etc"
create_ramdisk_dir "/tmp"
mkdir -v /root_bypass_ramdisks

echo "password"
echo ${password}

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

# single-user mode, appropriate for chroot environment
# explicitly setting the runlevel prevents warnings after installing packages
export RUNLEVEL=1

# Unset lang variables to prevent locale settings leaking from host
unset "${!LC_@}"
unset "${!LANG@}"

# set locale to en_US
echo "set locale to en_US"
echo "en_US.UTF-8 UTF-8" > /etc/locale.gen
dpkg-reconfigure locales

# Aliases
echo  "alias ll='ls -al'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo='sudo systemctl stop odoo; sudo -u odoo /usr/bin/python3 /home/pi/odoo/odoo-bin --config /home/pi/odoo.conf'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo_logs='less +F /var/log/odoo/odoo-server.log'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias write_mode='sudo mount -o remount,rw / && sudo mount -o remount,rw /root_bypass_ramdisks'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo_conf='cat /home/pi/odoo.conf'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias read_mode='sudo mount -o remount,ro / && sudo mount -o remount,ro /root_bypass_ramdisks'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias install='sudo mount -o remount,rw / && sudo mount -o remount,rw /root_bypass_ramdisks; sudo chroot /root_bypass_ramdisks/; mount -t proc proc /proc'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias blackbox='ls /dev/serial/by-path/'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias nano='write_mode; sudo -u odoo nano -l'" | tee -a /home/pi/.bashrc
echo  "alias vim='write_mode; sudo -u odoo vim -u /home/pi/.vimrc'" | tee -a /home/pi/.bashrc
echo  "alias odoo_luxe='printf \" ______\n< Luxe >\n ------\n        \\   ^__^\n         \\  (oo)\\_______\n            (__)\\       )\\/\\ \n                ||----w |\n                ||     ||\n\"'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo_start='sudo systemctl start odoo'" >> /home/pi/.bashrc
echo  "alias odoo_stop='sudo systemctl stop odoo'" >> /home/pi/.bashrc
echo  "alias odoo_restart='sudo systemctl restart odoo'" >> /home/pi/.bashrc
echo "
odoo_help() {
  echo '-------------------------------'
  echo ' Welcome to Odoo IoT Box tools'
  echo '-------------------------------'
  echo ''
  echo 'odoo                  Starts/Restarts Odoo server manually (not through odoo.service)'
  echo 'odoo_logs             Displays Odoo server logs in real time'
  echo 'odoo_conf             Displays Odoo configuration file content'
  echo 'write_mode            Enables system write mode'
  echo 'read_mode             Switches system to read-only mode'
  echo 'install               Bypasses ramdisks to allow package installation'
  echo 'blackbox              Lists all serial connected devices'
  echo 'odoo_start            Starts Odoo service'
  echo 'odoo_stop             Stops Odoo service'
  echo 'odoo_restart          Restarts Odoo service'
  echo 'odoo_dev <branch>     Resets Odoo on the specified branch from odoo-dev repository'
  echo 'odoo_origin <branch>  Resets Odoo on the specified branch from the odoo repository'
  echo 'devtools              Enables/Disables specific functions for development (more help with devtools help)'
  echo ''
  echo 'Odoo IoT online help: <https://www.odoo.com/documentation/master/applications/general/iot.html>'
}

odoo_dev() {
  if [ -z \"\$1\" ]; then
    odoo_help
    return
  fi
  write_mode
  pwd=\$(pwd)
  cd /home/pi/odoo
  sudo -u odoo git remote add dev https://github.com/odoo-dev/odoo.git
  sudo -u odoo git fetch dev \$1 --depth=1 --prune
  sudo -u odoo git reset --hard FETCH_HEAD
  sudo -u odoo git branch -m \$1
  sudo chroot /root_bypass_ramdisks /bin/bash -c \"export DEBIAN_FRONTEND=noninteractive && xargs apt-get -y -o Dpkg::Options::=\"--force-confdef\" -o Dpkg::Options::=\"--force-confold\" install < /home/pi/odoo/addons/iot_box_image/configuration/packages.txt\"
  sudo -u odoo pip3 install -r /home/pi/odoo/addons/iot_box_image/configuration/requirements.txt --break-system-package
  cd \$pwd
}

odoo_origin() {
  if [ -z \"\$1\" ]; then
    odoo_help
    return
  fi
  write_mode
  pwd=\$(pwd)
  cd /home/pi/odoo
  sudo -u odoo git remote set-url origin https://github.com/odoo/odoo.git  # ensure odoo repository
  sudo -u odoo git fetch origin \$1 --depth=1 --prune
  sudo -u odoo git reset --hard FETCH_HEAD
  sudo -u odoo git branch -m \$1
  sudo chroot /root_bypass_ramdisks /bin/bash -c \"export DEBIAN_FRONTEND=noninteractive && xargs apt-get -y -o Dpkg::Options::=\"--force-confdef\" -o Dpkg::Options::=\"--force-confold\" install < /home/pi/odoo/addons/iot_box_image/configuration/packages.txt\"
  sudo -u odoo pip3 install -r /home/pi/odoo/addons/iot_box_image/configuration/requirements.txt --break-system-package
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
  pip3 \"\$1\" \"\$2\" --break-system-package \"\$additional_arg\"
}

devtools() {
  help_message() {
    echo 'Usage: devtools <enable/disable> <general/actions> [action name]'
    echo ''
    echo 'Only provide an action name if you want to enable/disable a specific device action.'
    echo 'If no action name is provided, all actions will be enabled/disabled.'
    echo 'To enable/disable multiple actions, enclose them in quotes separated by commas.'
  }
  case \"\$1\" in
    enable|disable)
      case \"\$2\" in
        general|actions|longpolling)
          write_mode
          if ! grep -q '^\[devtools\]' /home/pi/odoo.conf; then
            sudo -u odoo bash -c \"printf '\n[devtools]\n' >> /home/pi/odoo.conf\"
          fi
          if [ \"\$1\" == \"disable\" ]; then
            value=\"\${3:-*}\" # Default to '*' if no action name is provided
            devtools enable \"\$2\" # Remove action/general/longpolling from conf to avoid duplicate keys
            write_mode
            sudo sed -i \"/^\[devtools\]/a\\\\\$2 = \$value\" /home/pi/odoo.conf
          elif [ \"\$1\" == \"enable\" ]; then
            sudo sed -i \"/\[devtools\]/,/\[/{/\$2 =/d}\" /home/pi/odoo.conf
          fi
          read_mode
          ;;
        *)
          help_message
          return 1
          ;;
      esac
      ;;
    *)
      help_message
      return 1
      ;;
  esac
}
" | tee -a ~/.bashrc /home/pi/.bashrc

# Change default hostname from 'raspberrypi' to 'iotbox'
echo iotbox | tee /etc/hostname
sed -i 's/\braspberrypi/iotbox/g' /etc/hosts

apt-get update

# At the first start it is necessary to configure a password
# This will be modified by a unique password on the first start of Odoo
password="$(openssl rand -base64 12)"
echo "pi:${password}" | chpasswd
echo TrustedUserCAKeys /etc/ssh/ca.pub >> /etc/ssh/sshd_config

PKGS_TO_INSTALL="
    arp-scan \
    chromium-browser \
    console-data \
    cups \
    cups-ipp-utils \
    dbus \
    dnsmasq \
    fswebcam \
    git \
    hostapd \
    iw \
    kpartx \
    labwc \
    libcups2-dev \
    libpq-dev \
    libffi-dev \
    localepurge \
    mtr \
    nginx-full \
    printer-driver-all \
    python3 \
    python3-aioice \
    python3-cups \
    python3-crc32c \
    python3-cryptography \
    python3-babel \
    python3-dateutil \
    python3-dbus \
    python3-decorator \
    python3-dev \
    python3-docutils \
    python3-geoip2 \
    python3-jinja2 \
    python3-ldap \
    python3-libsass \
    python3-libcamera \
    python3-lxml \
    python3-mako \
    python3-mock \
    python3-netifaces \
    python3-openssl \
    python3-passlib \
    python3-pil \
    python3-pip \
    python3-psutil \
    python3-psycopg2 \
    python3-pydot \
    python3-pyee \
    python3-pylibsrtp \
    python3-pyudev \
    python3-qrcode \
    python3-reportlab \
    python3-requests \
    python3-serial \
    python3-stdnum \
    python3-tz \
    python3-vobject \
    python3-zeroconf \
    rsync \
    screen \
    seatd \
    swaybg \
    swig \
    vim \
    wlr-randr \
    xdotool"

# Prevent Wi-Fi blocking
apt-get -y remove rfkill

echo "Acquire::Retries "16";" > /etc/apt/apt.conf.d/99acquire-retries
# KEEP OWN CONFIG FILES DURING PACKAGE CONFIGURATION
# http://serverfault.com/questions/259226/automatically-keep-current-version-of-config-files-when-apt-get-install
apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install ${PKGS_TO_INSTALL}
apt-get -y autoremove

apt-get clean
localepurge
rm -rfv /usr/share/doc

# Remove the default nginx website, we have our own config in /etc/nginx/conf.d/
rm /etc/nginx/sites-enabled/default

# python-usb in wheezy is too old
# the latest pyusb from pip does not work either, usb.core.find() never returns
# this may be fixed with libusb>2:1.0.11-1, but that's the most recent one in raspios
# so we install the latest pyusb that works with this libusb.
# Even in stretch, we had an error with langid (but worked otherwise)
# We fixe the version of evdev to 1.2.0 because in 1.3.0 we have a RuntimeError in 'get_event_loop()'
PIP_TO_INSTALL="
    evdev==1.6.0 \
    gatt \
    polib \
    pycups \
    pyusb \
    v4l2 \
    pysmb==1.2.9.1 \
    cryptocode==0.1 \
    PyKCS11 \
    vcgencmd \
    RPi.GPIO \
    rjsmin==1.1.0 \
    websocket-client==1.6.3 \
    PyPDF2==1.26.0 \
    Werkzeug==2.0.2 \
    urllib3==1.26.5 \
    python-escpos==3.1 \
    screeninfo==0.8.1 \
    zeep==4.2.1 \
    num2words==0.5.13 \
    freezegun==1.2.1 \
    schedule==1.2.1"

pip3 install ${PIP_TO_INSTALL} --break-system-package

# Dowload MPD server and library for Six terminals
wget 'https://nightly.odoo.com/master/iotbox/eftdvs' -P /usr/local/bin/
chmod +x /usr/local/bin/eftdvs
wget 'https://nightly.odoo.com/master/iotbox/eftapi.so' -P /usr/lib/

# Create Odoo user for odoo service and disable password login
adduser --disabled-password --gecos "" --shell /usr/sbin/nologin odoo

# Replace pi user with odoo user in sudoers file: odoo user doesn't need to type its password to run sudo commands
mv /etc/sudoers.d/010_pi-nopasswd /etc/sudoers.d/010_odoo-nopasswd
sed -i 's/pi/odoo/g' /etc/sudoers.d/010_odoo-nopasswd

# copy the odoo.conf file to the overwrite directory
mv -v "/home/pi/odoo/addons/iot_box_image/configuration/odoo.conf" "/home/pi/"
chown odoo:odoo "/home/pi/odoo.conf"

groupadd usbusers
usermod -a -G usbusers odoo
usermod -a -G video odoo
usermod -a -G render odoo
usermod -a -G lp odoo
usermod -a -G input odoo
usermod -a -G dialout odoo
usermod -a -G pi odoo
mkdir -v /var/log/odoo
chown odoo:odoo /var/log/odoo
chown odoo:odoo -R /home/pi/odoo/

# logrotate is very picky when it comes to file permissions
chown -R root:root /etc/logrotate.d/
chmod -R 644 /etc/logrotate.d/
chown root:root /etc/logrotate.conf
chmod 644 /etc/logrotate.conf

update-rc.d -f hostapd remove
update-rc.d -f nginx remove
update-rc.d -f dnsmasq remove

systemctl enable ramdisks.service
systemctl disable dphys-swapfile.service
systemctl enable ssh
systemctl set-default graphical.target
systemctl disable getty@tty1.service
systemctl disable systemd-timesyncd.service
systemctl unmask hostapd.service
systemctl disable hostapd.service
systemctl disable cups-browsed.service
systemctl enable labwc.service
systemctl enable odoo.service
systemctl enable odoo-led-manager.service
systemctl enable odoo-ngrok.service

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

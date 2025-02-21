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
echo  "alias odoo='sudo systemctl stop odoo; sudo /usr/bin/python3 /home/pi/odoo/odoo-bin --config /home/pi/odoo.conf'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo_logs='less +F /var/log/odoo/odoo-server.log'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias write_mode='sudo mount -o remount,rw / && sudo mount -o remount,rw /root_bypass_ramdisks'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias odoo_conf='cat /home/pi/odoo.conf'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias read_mode='sudo mount -o remount,ro / && sudo mount -o remount,ro /root_bypass_ramdisks'" | tee -a ~/.bashrc /home/pi/.bashrc
echo  "alias install='sudo mount -o remount,rw / && sudo mount -o remount,rw /root_bypass_ramdisks && sudo chroot /root_bypass_ramdisks/'" | tee -a ~/.bashrc /home/pi/.bashrc
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
  sudo git config --global --add safe.directory /home/pi/odoo
  sudo git remote add dev https://github.com/odoo-dev/odoo.git
  sudo git fetch dev \$1 --depth=1 --prune
  sudo git reset --hard dev/\$1
  sudo chown -R odoo:odoo /home/pi/odoo
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
  sudo git config --global --add safe.directory /home/pi/odoo
  sudo git remote set-url origin https://github.com/odoo/odoo.git  # ensure odoo repository
  sudo git fetch origin \$1 --depth=1 --prune
  sudo git reset --hard origin/\$1
  sudo chown -R odoo:odoo /home/pi/odoo
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
        general|actions)
          write_mode
          if ! grep -q '^\[devtools\]' /home/pi/odoo.conf; then
            sudo -u odoo bash -c \"printf '\n[devtools]\n' >> /home/pi/odoo.conf\"
          fi
          if [ \"\$1\" == \"disable\" ]; then
            value=\"\${3:-*}\" # Default to '*' if no action name is provided
            devtools enable \"\$2\" # Remove action/general from conf to avoid duplicate keys
            write_mode
            sudo -u odoo sed -i \"/^\[devtools\]/a\\\\\$2 = \$value\" /home/pi/odoo.conf
          elif [ \"\$1\" == \"enable\" ]; then
            sudo -u odoo sed -i \"/\[devtools\]/,/\[/{/\$2 =/d}\" /home/pi/odoo.conf
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

source ~/.bashrc
source /home/pi/.bashrc

apt-get update

# At the first start it is necessary to configure a password
# This will be modified by a unique password on the first start of Odoo
password="$(openssl rand -base64 12)"
echo "pi:${password}" | chpasswd

echo "Acquire::Retries "16";" > /etc/apt/apt.conf.d/99acquire-retries
# KEEP OWN CONFIG FILES DURING PACKAGE CONFIGURATION
# http://serverfault.com/questions/259226/automatically-keep-current-version-of-config-files-when-apt-get-install
xargs apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install < /home/pi/odoo/addons/iot_box_image/configuration/packages.txt
apt-get -y autoremove

apt-get clean
localepurge
rm -rfv /usr/share/doc

pip3 install -r /home/pi/odoo/addons/iot_box_image/configuration/requirements.txt --break-system-package

# Dowload MPD server and library for Six terminals
wget 'https://nightly.odoo.com/master/iotbox/eftdvs' -P /usr/local/bin/
chmod +x /usr/local/bin/eftdvs
wget 'https://nightly.odoo.com/master/iotbox/eftapi.so' -P /usr/lib/

# Create Odoo user for odoo service and disable password login
adduser --disabled-password --gecos "" --shell /usr/sbin/nologin odoo

# Replace pi user with odoo user in sudoers file: odoo user doesn't need to type its password to run sudo commands
mv /etc/sudoers.d/010_pi-nopasswd /etc/sudoers.d/010_odoo-nopasswd
sed -i 's/pi/odoo/g' /etc/sudoers.d/010_odoo-nopasswd

# Allow "sudo" git commands even if Odoo directory is owned by odoo user
git config --global --add safe.directory /home/pi/odoo

# copy the odoo.conf file to the overwrite directory
mv -v "/home/pi/odoo/addons/iot_box_image/configuration/odoo.conf" "/home/pi/"
chown odoo:odoo "/home/pi/odoo.conf"

groupadd usbusers
usermod -a -G usbusers odoo
usermod -a -G video odoo
usermod -a -G lp odoo
usermod -a -G input lightdm
usermod -a -G input odoo
usermod -a -G pi odoo
mkdir -v /var/log/odoo
chown odoo:odoo /var/log/odoo
chown odoo:odoo -R /home/pi/odoo/

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
systemctl disable dphys-swapfile.service
systemctl enable ssh
systemctl set-default graphical.target
systemctl disable getty@tty1.service
systemctl enable systemd-timesyncd.service
systemctl unmask hostapd.service
systemctl disable hostapd.service
systemctl disable cups-browsed.service
systemctl enable odoo.service

# ========= BOOT FILE CONFIGURATION =========
# Related documentation:
# https://www.raspberrypi.com/documentation/computers/legacy_config_txt.html
BOOT_CONFIG_FILE="/boot/config.txt"

# disable overscan in /boot/config.txt, we can't use
# overwrite_after_init because it's on a different device
# (/dev/mmcblk0p1) and we don't mount that afterwards.
# This option disables any black strips around the screen
# cf: https://www.raspberrypi.org/documentation/configuration/raspi-config.md
echo "disable_overscan=1" >> ${BOOT_CONFIG_FILE}

# Allow to detect displays after boot
echo "hdmi_force_hotplug=1" >> ${BOOT_CONFIG_FILE} # HDMI output mode will be used, even if no HDMI monitor is detected
echo "​hdmi_force_mode=1" >> ${BOOT_CONFIG_FILE} # Allow forced options below
echo "hdmi_group=0" >> ${BOOT_CONFIG_FILE} # Automatically detect hdmi group
echo "hdmi_mode=16" >> ${BOOT_CONFIG_FILE} # 1080p 60Hz 16:9
echo "hdmi_ignore_edid=0xa5000080" >> ${BOOT_CONFIG_FILE} # safeguard against invalid display EDID

# Use the fkms driver instead of the legacy one (RPI3 requires this)
sed -i '/dtoverlay/c\dtoverlay=vc4-fkms-v3d' ${BOOT_CONFIG_FILE}

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

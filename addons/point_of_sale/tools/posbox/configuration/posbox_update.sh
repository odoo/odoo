#!/usr/bin/env bash

sudo mount -o remount,rw /

# As we got an error of diverged branches in the case of git pull,
# we fetch and checkout the remote branch, delete the local branch and
# set the remote branch to be the new original one
sudo git --work-tree=/home/pi/odoo/ --git-dir=/home/pi/odoo/.git fetch --depth=1
sudo git --work-tree=/home/pi/odoo/ --git-dir=/home/pi/odoo/.git checkout origin/12.0
sudo git --work-tree=/home/pi/odoo/ --git-dir=/home/pi/odoo/.git branch -D 12.0
sudo git --work-tree=/home/pi/odoo/ --git-dir=/home/pi/odoo/.git checkout -b 12.0
sudo mount -o remount,ro /
(sleep 5 && sudo reboot) &

#!/usr/bin/env bash

sudo mount -o remount,rw /
sudo git --work-tree=/home/pi/odoo/ --git-dir=/home/pi/odoo/.git pull
sudo mount -o remount,ro /
(sleep 5 && sudo reboot) &

#!/usr/bin/env bash

sudo mount -o remount,rw /

cd /home/pi/odoo
localbranch=$(git symbolic-ref -q --short HEAD)
localremote=$(git config branch.$localbranch.remote)
git fetch "${localremote}" "${localbranch}" --depth=1
git reset "${localremote}"/"${localbranch}" --hard
sudo mount -o remount,ro /
(sleep 5 && sudo reboot) &

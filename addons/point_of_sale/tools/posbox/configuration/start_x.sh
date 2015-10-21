#!/usr/bin/env bash

# Start X if it hasn't been started yet, tvservice -n is the best way
# I could find to detect whether or not a display was attached. We
# also redefine $HOME because X wants to write in it and we don't have
# a /home ramdisk.
if [ -z "$(tvservice -n 2>&1 | grep 'No device present')" ] && [ -z $DISPLAY ] ; then
    sudo -iu pi HOME="/tmp" xinit /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/x_application.sh
fi

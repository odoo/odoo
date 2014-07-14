#!/bin/bash 
echo "Killing all Odoo processes"
killall python;
echo "Stopping Odoo Service"
sudo systemctl stop odoo.service;
echo "Removing PID File"
rm -f /home/pi/odoo/posbox.pid;

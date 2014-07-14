#!/bin/bash 
echo "Terminating Odoo Server"
killall python;
sleep 1
killall python;
echo "Restarting Odoo Server"
sudo systemctl restart odoo.service;
echo "Done"
sudo systemctl status odoo.service;

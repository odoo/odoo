#!/bin/bash -x
cp 99-usb.rules /etc/udev/rules.d/99-usb.rules;
cp README ~/README;
cp odoo.service /etc/systemd/system/odoo.service;

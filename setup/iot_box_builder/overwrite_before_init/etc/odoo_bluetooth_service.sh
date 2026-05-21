#!/bin/bash

# send stdout and stderr to a log file
exec 1>/var/log/odoo_bluetooth_service.log 2>&1

_IP=$(hostname -I) || "No network connection"
_SERIAL=$(cat /sys/firmware/devicetree/base/serial-number)
_BLUETOOTH_HOSTNAME="IoT Box ${_SERIAL} - ip ${_IP}"

# Start Bluetooth on the iot box and advertise the IoT Box serial number with the IP address
rfkill unblock bluetooth
bluetoothctl power on
bluetoothctl system-alias "${_BLUETOOTH_HOSTNAME}"
bluetoothctl discoverable-timeout 300
bluetoothctl discoverable on

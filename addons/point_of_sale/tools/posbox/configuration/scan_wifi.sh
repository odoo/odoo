#!/usr/bin/env bash
logger -t posbox_scan_wifi "Starting scanning wifi"
sudo iwlist wlan0 scan | grep 'ESSID:' | sed 's/.*ESSID:"\(.*\)"/\1/' > /tmp/scanned_networks.txt

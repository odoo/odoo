#!/usr/bin/env bash

CURRENT_WIFI_NETWORK_FILE="/tmp/current_wifi_network.txt"
while true ; do
	if [ -z "$(cat <(ifconfig eth0) <(ifconfig wlan0) | grep "inet addr" | awk -F: '{print $2}' | awk '{print $1}';)" ] ; then
		ESSID=$(head -n 1 "${CURRENT_WIFI_NETWORK_FILE}" | tr -d '\n')
		PASSWORD=$(tail -n 1 "${CURRENT_WIFI_NETWORK_FILE}" | tr -d '\n')

		logger -t posbox_keep_wifi_alive "Lost wifi, trying to reconnect to ${ESSID}"

		sudo /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/connect_to_wifi.sh "${ESSID}" "${PASSWORD}" "" "NO_AP"

		sleep 30
	fi

	sleep 2
done

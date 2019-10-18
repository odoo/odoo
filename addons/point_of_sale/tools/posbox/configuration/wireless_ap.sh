#!/usr/bin/env bash

FORCE_HOST_AP="${1}"
WIRED_IP=$(python3 -c "import netifaces as ni; print(ni.ifaddresses('eth0').get(ni.AF_INET) and ni.ifaddresses('eth0')[ni.AF_INET][0]['addr'] or '')")
WIFI_NETWORK_FILE="/home/pi/wifi_network.txt"


ifconfig wlan0 down
ifconfig wlan0 up

# wait for wlan0 to come up
sleep 5

# if there is no wired ip, attempt to start an AP through wireless interface
if [ -z "${WIRED_IP}" ] ; then
	logger -t posbox_wireless_ap "No wired IP"

	if [ -f "${WIFI_NETWORK_FILE}" ] && [ -z "${FORCE_HOST_AP}" ] ; then
		logger -t posbox_wireless_ap "Loading persistently saved setting"
		/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/connect_to_wifi.sh &
	else
		logger -t posbox_wireless_ap "Starting AP"

		service hostapd restart

		ip addr add 10.11.12.1/24 dev wlan0

		service dnsmasq restart

		service nginx stop
		# We start nginx in another configuration than the default one with https
		# as it needs to do redirect instead in case the IoT Box acts as an ap
		nginx -c /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/nginx_ap.conf

		service odoo restart
	fi
# wired
else
	killall nginx
	service nginx restart
	service dnsmasq stop
	service odoo restart
fi

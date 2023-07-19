#!/usr/bin/env bash

FORCE_HOST_AP="${1}"
WIFI_NETWORK_FILE="/home/pi/wifi_network.txt"
COUNTER=0

# we need to wait to receive an ip address from the dhcp before enable the access point.
# only if only if no configuration file for the wifi networks is recorded
if ! [ -f "${WIFI_NETWORK_FILE}" ] && [ -z "${FORCE_HOST_AP}" ] ; then
	while [ "$(hostname -I)" = '' ] && [ "$COUNTER" -le 10 ]; do sleep 2;((COUNTER++)); done
fi

WIRED_IP=$(hostname -I)

if [ "$WIRED_IP" ]; then
  printf "My IP address is %s\n" "$WIRED_IP"
fi

# by default wlan0 is soft blocked.
# we need unblock all radio devices
rfkill unblock all
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

		SSID=$(grep -oP '(?<=ssid=).*' /etc/hostapd/hostapd.conf)

		if [ "${SSID}" = "IoTBox" ]
		then
			# override SSID to get a unique SSID
			MAC=$(ip link show wlan0 | tail -n 1 | awk '{print $2}' | sed 's/\://g')
			NEWSSID="${SSID}-${MAC}"
			sed -ie "s/$(echo ${SSID})/$(echo ${NEWSSID})/g" /etc/hostapd/hostapd.conf
		fi

		service hostapd restart

		ip addr add 10.11.12.1/24 dev wlan0

		service dnsmasq restart

		service odoo restart
	fi
# wired
else
	killall nginx
	service nginx restart
	service dnsmasq stop
	service odoo restart
fi

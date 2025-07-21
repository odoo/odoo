#!/usr/bin/env bash

function get_conf () {
    KEY="${1}"
    CONF_FILE="${2}"
    # These commands seek for keys on the configuration file,
    # for each key found, trim spaces and store the corresponding value

    touch "$CONF_FILE"  # create the file if it does not exist
    awk -v key="$KEY" -F= '$1 ~ "^" key "[[:space:]]*" {gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2}' "$CONF_FILE"
}

FORCE_HOST_AP="${1}"
CONF_FILE="/home/pi/odoo.conf"
COUNTER=0
ESSID=$(get_conf "wifi_ssid" "${CONF_FILE}")
PASSWORD=$(get_conf "wifi_password" "${CONF_FILE}")

# we need to wait to receive an ip address from the dhcp before enable the access point.
# only if no configuration file for the wifi networks is recorded
if ! [ "${ESSID}" ] && [ "${PASSWORD}" ] && [ -z "${FORCE_HOST_AP}" ] ; then
	while [ "$(hostname -I)" = '' ] && [ "$COUNTER" -le 10 ]; do sleep 2;((COUNTER++)); done
fi

# Do we have to use the NetworkManager ?
current_iotbox_version=$(cat "/var/odoo/iotbox_version")
required_version="23.11"
if [[ "$current_iotbox_version" < "$required_version" ]]; then
    logger -t wireless_ap "USING WPA_SUPPLICANT REMOVING NETWORK MANAGER SERVICE"
    sudo service NetworkManager stop
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

	if [ "${ESSID}" ] && [ "${PASSWORD}" ] && [ -z "${FORCE_HOST_AP}" ] ; then
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
		service odoo restart # As this file is executed on boot, this line is responsible for restarting odoo service on reboot
	fi
# wired
else
	killall nginx
	service nginx restart
	service dnsmasq stop
	ip addr del 10.11.12.1/24 dev wlan0 # remove the static ip
	service odoo restart # As this file is executed on boot, this line is responsible for restarting odoo service on reboot
fi

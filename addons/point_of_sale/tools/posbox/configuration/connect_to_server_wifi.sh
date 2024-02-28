#!/usr/bin/env bash

# Write the server configuration
# call with ESSID and optionally a password
# when called without an ESSID, it will attempt
# to reconnect to a previously chosen network
function connect () {
	SERVER="${1}"
	CONF_FILE=/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/odoo.conf
	HOSTS=/root_bypass_ramdisks/etc/hosts
	HOST_FILE=/root_bypass_ramdisks/etc/hostname
	HOSTNAME="$(hostname)"
	TOKEN="${3}"
	IOT_NAME="${2}"
	IOT_NAME="${IOT_NAME//[^[:ascii:]]/}"
	IOT_NAME="${IOT_NAME//[^a-zA-Z0-9-]/}"
	if [ -z "$IOT_NAME" ]
	then
		IOT_NAME="${HOSTNAME}"
	fi
	sudo mount -o remount,rw /
	sudo mount -o remount,rw /root_bypass_ramdisks
	if [ ! -z "${1}" ]
	then
		# These commands seeks for keys on the configuration file, 
		# for each key found replace/create the corresponding value
		sed -i "s/^\b\(odoo_remote_server\)\b.*/\1 = $SERVER/" "$CONF_FILE"
		sed -i "s/^\b\(token\)\b.*/\1 = $TOKEN/" "$CONF_FILE"
	fi
	if [ "${IOT_NAME}" != "${HOSTNAME}" ]
	then
		sudo sed -i "s/${HOSTNAME}/${IOT_NAME}/g" ${HOSTS}
		echo "${IOT_NAME}" > /tmp/hostname
		sudo cp /tmp/hostname "${HOST_FILE}"

		echo "interface=wlan0" > /root_bypass_ramdisks/etc/hostapd/hostapd.conf
		echo "ssid=${IOT_NAME}" >> /root_bypass_ramdisks/etc/hostapd/hostapd.conf
		echo "channel=1" >> /root_bypass_ramdisks/etc/hostapd/hostapd.conf
		
		sudo hostname "${IOT_NAME}"
	fi
	sudo mount -o remount,ro /
	sudo mount -o remount,ro /root_bypass_ramdisks

	WPA_PASS_FILE="/tmp/wpa_pass.txt"
	CURRENT_WIFI_NETWORK_FILE="/tmp/current_wifi_network.txt" # used to repair connection when we lose it
	LOST_WIFI_FILE="/tmp/lost_wifi.txt"
	ESSID="${4}"
	PASSWORD="${5}"
	NO_AP="${6}"

	sleep 3

	sudo pkill -f keep_wifi_alive.sh
	WIFI_WAS_LOST=$?

	if [ -n "${ESSID}" ] ; then
		logger -t posbox_connect_to_wifi "Making network selection permanent"
		sudo mount -o remount,rw /
		# These commands seek for keys on the configuration file, 
		# for each key found replace/create the corresponding value
		sed -i "s/^\b\(wifi_ssid\)\b.*/\1 = $ESSID/" "$CONF_FILE"
		sed -i "s/^\b\(wifi_password\)\b.*/\1 = $PASSWORD/" "$CONF_FILE"
		sudo mount -o remount,ro /
	else
		logger -t posbox_connect_to_wifi "Reading configuration from ${CONF_FILE}"
		# These commands seek for keys on the configuration file, 
		# for each key found, trim spaces and store the corresponding value
		ESSID=$(awk -F= '$1~/^(wifi_ssid)[[:space:]]*/ {gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2}' "$CONF_FILE")
		PASSWORD=$(awk -F= '$1~/^(wifi_password)[[:space:]]*/ {gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2}' "$CONF_FILE")
	fi

	echo "${ESSID}" > ${CURRENT_WIFI_NETWORK_FILE}
	echo "${PASSWORD}" >> ${CURRENT_WIFI_NETWORK_FILE}

	logger -t posbox_connect_to_server_wifi "Connecting to ${ESSID}"
	sudo service hostapd stop

	sudo killall nginx

	current_iotbox_version=$(cat "/var/odoo/iotbox_version")
	# Above this version we need the NetworkManager
	required_version="23.09"
	if [[ "$current_iotbox_version" > "$required_version" ]]; then
		logger -t posbox_connect_to_server_wifi "USING NETWORK MANAGER"
		# Necessary when comming from the access point
		sudo ip address del 10.11.12.1/24 dev wlan0
		sudo nmcli g reload
		if [ -z "${PASSWORD}" ] ; then
			sudo nmcli d wifi connect "${ESSID}"
		else
			sudo nmcli d wifi connect "${ESSID}" password "${PASSWORD}"
		fi
		sudo service nginx restart
	else
		logger -t posbox_connect_to_server_wifi "USING WPA_SUPPLICANT"
		sudo service nginx restart
		sudo service dnsmasq stop

		sudo pkill wpa_supplicant
		sudo ifconfig wlan0 down
		sudo ifconfig wlan0 0.0.0.0  # this is how you clear the interface's configuration
		sudo ifconfig wlan0 up

		if [ -z "${PASSWORD}" ] ; then
			sudo iwconfig wlan0 essid "${ESSID}"
		else
			# Necessary in stretch: https://www.raspberrypi.org/forums/viewtopic.php?t=196927
			sudo cp /etc/wpa_supplicant/wpa_supplicant.conf "${WPA_PASS_FILE}"
			sudo chmod 777 "${WPA_PASS_FILE}"
			sudo wpa_passphrase "${ESSID}" "${PASSWORD}" >> "${WPA_PASS_FILE}"
			sudo wpa_supplicant -B -i wlan0 -c "${WPA_PASS_FILE}"
		fi

		sudo systemctl daemon-reload
		sudo service dhcpcd restart
	fi

	# give dhcp some time
	timeout 30 sh -c 'until ifconfig wlan0 | grep "inet " ; do sleep 0.1 ; done'
	TIMEOUT_RETURN=$?


	if [ ${TIMEOUT_RETURN} -eq 124 ] && [ -z "${NO_AP}" ] ; then
		logger -t posbox_connect_to_server_wifi "Failed to connect, forcing Posbox AP"
		sudo /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/wireless_ap.sh "force" &
	else
		if [ ${TIMEOUT_RETURN} -ne 124 ] ; then
			rm -f "${LOST_WIFI_FILE}"
		fi

		if [ ! -f "${LOST_WIFI_FILE}" ] ; then
			logger -t posbox_connect_to_server_wifi "Restarting odoo"
		fi

		if [ ${WIFI_WAS_LOST} -eq 0 ] ; then
			touch "${LOST_WIFI_FILE}"
		fi

		logger -t posbox_connect_to_server_wifi "Starting wifi keep alive script"
		/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/keep_wifi_alive.sh &
	fi

	if [ "${IOT_NAME}" != "${HOSTNAME}" ]
	then
		sudo reboot
	else
		sudo service odoo restart
	fi
}

connect "${1}" "${2}" "${3}" "${4}" "${5}" "${6}" &

#!/usr/bin/env bash

function connect () {
	NV_FS=/root_bypass_ramdisks
	HOSTNAME="$(hostname)"
	CURRENT_SERVER_FILE=/home/pi/odoo-remote-server.conf
	HOSTS=${NV_FS}/etc/hosts
	HOST_FILE=${NV_FS}/etc/hostname
	TOKEN_FILE=/home/pi/token
	WPA_PASS_FILE="/tmp/wpa_pass.txt"
	PERSISTENT_WIFI_NETWORK_FILE="/home/pi/wifi_network.txt"
	CURRENT_WIFI_NETWORK_FILE="/tmp/current_wifi_network.txt" # used to repair connection when we lose it
	LOST_WIFI_FILE="/tmp/lost_wifi.txt"
	ESSID="${1}"
	PASSWORD="${2}"
	PERSIST="${3}"
	SERVER="${4}"
	TOKEN="${5}"
	IOT_NAME="${6}"
	NO_AP="${7}"

	if [ ! -z "${SERVER}" ]
	then
		logger -t posbox_connect_to_wifi "Creating/Saving ${CURRENT_SERVER_FILE} for ${SERVER}"
		logger -t posbox_connect_to_wifi "Creating/Saving ${TOKEN_FILE} file for ${TOKEN}"
		sudo mount -o remount,rw /
		echo "${SERVER}" > ${CURRENT_SERVER_FILE}
		echo "${TOKEN}" > ${TOKEN_FILE}
		sudo mount -o remount,ro /
	fi

	sleep 3

	sudo pkill -f keep_wifi_alive.sh
	WIFI_WAS_LOST=$?

	# make network choice persistent
	if [ -n "${ESSID}" ] ; then
		if [ -n "${PERSIST}" ] ; then
			logger -t posbox_connect_to_wifi "Making network selection permanent"
			sudo mount -o remount,rw /
			echo "${ESSID}" > ${PERSISTENT_WIFI_NETWORK_FILE}
			echo "${PASSWORD}" >> ${PERSISTENT_WIFI_NETWORK_FILE}
			sudo mount -o remount,ro /
		fi
	else
		logger -t posbox_connect_to_wifi "Reading configuration from ${PERSISTENT_WIFI_NETWORK_FILE}"
		ESSID=$(head -n 1 "${PERSISTENT_WIFI_NETWORK_FILE}" | tr -d '\n')
		PASSWORD=$(tail -n 1 "${PERSISTENT_WIFI_NETWORK_FILE}" | tr -d '\n')
	fi

	echo "${ESSID}" > ${CURRENT_WIFI_NETWORK_FILE}
	echo "${PASSWORD}" >> ${CURRENT_WIFI_NETWORK_FILE}

	logger -t posbox_connect_to_wifi "Connecting to ${ESSID}"
	sudo service hostapd stop
	# Necessary when comming from the access point
	sudo ip address del 10.11.12.1/24 dev wlan0
	sudo killall nginx

	sudo nmcli g reload

	if [ -z "${PASSWORD}" ] ; then
		sudo nmcli d wifi connect "${ESSID}"
	else
		sudo nmcli d wifi connect "${ESSID}" password "${PASSWORD}"
	fi

	sudo service nginx restart

	# give dhcp some time
	timeout 30 sh -c 'until ifconfig wlan0 | grep "inet " ; do sleep 0.1 ; done'
	TIMEOUT_RETURN=$?


	if [ ${TIMEOUT_RETURN} -eq 124 ] && [ -z "${NO_AP}" ] ; then
		logger -t posbox_connect_to_wifi "Failed to connect, forcing Posbox AP"
		sudo /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/wireless_ap.sh "force" &
	else
		if [ ${TIMEOUT_RETURN} -ne 124 ] ; then
			rm -f "${LOST_WIFI_FILE}"
		fi

		if [ ! -f "${LOST_WIFI_FILE}" ] ; then
			logger -t posbox_connect_to_wifi "Restarting odoo"
			sudo service odoo restart
		fi

		if [ ${WIFI_WAS_LOST} -eq 0 ] ; then
			touch "${LOST_WIFI_FILE}"
		fi

		logger -t posbox_connect_to_wifi "Starting wifi keep alive script"
		/home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/keep_wifi_alive.sh &
	fi

	if [ -n "${IOT_NAME}" ] && [ "${IOT_NAME}" != "${HOSTNAME}" ];
	then
		logger -t posbox_connect_to_wifi "Changing hostname from ${HOSTNAME} to ${IOT_NAME}"
		sudo nmcli g hostname ${IOT_NAME}
		sudo mount -o remount,rw ${NV_FS}
		sudo cp /etc/hostname "${HOST_FILE}"
		logger -t posbox_connect_to_wifi "REBOOT ..."
		sudo reboot
	else
		logger -t posbox_connect_to_wifi "Restarting odoo service"
		sudo service odoo restart
	fi
}

connect "${1}" "${2}" "${3}" "${4}" "${5}" "${6}" "${7}" &

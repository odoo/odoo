#!/usr/bin/env bash

function update_conf () {
  KEY="${1}"
  VALUE="${2}"
  CONF_FILE="${3}"

  # This command checks if the section exists in the configuration file.
  if ! grep -q "\[iot\.box\]" "$CONF_FILE"; then
    echo "[iot.box]" >> "$CONF_FILE"
  fi

  # These commands check if the key exists in the configuration file.
  # If the key exists, replace its value.
  # If the key does not exist, append the key-value pair to the configuration file.
  if grep -q "^\s*$KEY\b" "$CONF_FILE"; then
    # Key exists, replace its value
    sed -i "s/^\s*\b\($KEY\)\b.*/\1 = $VALUE/" "$CONF_FILE"
  else
    # Key does not exist, add key-value pair
    echo "$KEY = $VALUE" >> "$CONF_FILE"
  fi
}

function get_conf () {
  KEY="${1}"
  CONF_FILE="${2}"
  # These commands seek for keys on the configuration file,
  # for each key found, trim spaces and store the corresponding value

  touch "$CONF_FILE"  # create the file if it does not exist
  awk -v key="$KEY" -F= '$1 ~ "^" key "[[:space:]]*" {gsub(/^[[:space:]]+|[[:space:]]+$/, "", $2); print $2}' "$CONF_FILE"
}

# call with ESSID and optionally a password
# when called without an ESSID, it will attempt
# to reconnect to a previously chosen network
function connect () {
	WPA_PASS_FILE="/tmp/wpa_pass.txt"
	CONF_FILE="/home/pi/odoo.conf"
	CURRENT_WIFI_NETWORK_FILE="/tmp/current_wifi_network.txt" # used to repair connection when we lose it
	LOST_WIFI_FILE="/tmp/lost_wifi.txt"
	ESSID="${1}"
	PASSWORD="${2}"
	PERSIST="${3}"
	NO_AP="${4}"

	sleep 3

	sudo pkill -f keep_wifi_alive.sh
	WIFI_WAS_LOST=$?

	# make network choice persistent
	if [ -n "${ESSID}" ] ; then
	  if [ -n "${PERSIST}" ]; then
      logger -t posbox_connect_to_wifi "Making network selection permanent"
      sudo mount -o remount,rw /

      update_conf "wifi_ssid" "$ESSID" "$CONF_FILE"
      update_conf "wifi_password" "$PASSWORD" "$CONF_FILE"

      sudo mount -o remount,ro /
    fi
	else
		logger -t posbox_connect_to_wifi "Reading configuration from ${CONF_FILE}"

    ESSID=$(get_conf "wifi_ssid" "$CONF_FILE")
    PASSWORD=$(get_conf "wifi_password" "$CONF_FILE")
	fi

	echo "${ESSID}" > ${CURRENT_WIFI_NETWORK_FILE}
	echo "${PASSWORD}" >> ${CURRENT_WIFI_NETWORK_FILE}

	logger -t posbox_connect_to_wifi "Connecting to ${ESSID}"
	sudo service hostapd stop

	sudo killall nginx

	current_iotbox_version=$(cat "/var/odoo/iotbox_version")
	# Above this version we need the NetworkManager
	required_version="23.09"
	if [[ "$current_iotbox_version" > "$required_version" ]]; then
		logger -t posbox_connect_to_wifi "USING NETWORK MANAGER"
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
		logger -t posbox_connect_to_wifi "USING WPA_SUPPLICANT"
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
}

connect "${1}" "${2}" "${3}" "${4}" &

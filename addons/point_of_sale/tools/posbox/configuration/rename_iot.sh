#!/usr/bin/env bash

# Write the server configuration
function connect () {
	HOSTS=/root_bypass_ramdisks/etc/hosts
	HOST_FILE=/root_bypass_ramdisks/etc/hostname
	HOSTNAME="$(hostname)"
	IOT_NAME="${1}"
	IOT_NAME="${IOT_NAME//[^[:ascii:]]/}"
	IOT_NAME="${IOT_NAME//[^a-zA-Z0-9-]/}"
	if [ -z "$IOT_NAME" ]
	then
		IOT_NAME="${HOSTNAME}"
	fi
	if [ "${IOT_NAME}" != "${HOSTNAME}" ]
	then
    sudo mount -o remount,rw /
    sudo mount -o remount,rw /root_bypass_ramdisks

		sudo sed -i "s/${HOSTNAME}/${IOT_NAME}/g" ${HOSTS}
		echo "${IOT_NAME}" > /tmp/hostname
		sudo cp /tmp/hostname "${HOST_FILE}"

		echo "interface=wlan0" > /root_bypass_ramdisks/etc/hostapd/hostapd.conf
		echo "ssid=${IOT_NAME}" >> /root_bypass_ramdisks/etc/hostapd/hostapd.conf
		echo "channel=1" >> /root_bypass_ramdisks/etc/hostapd/hostapd.conf

		sudo hostname "${IOT_NAME}"
		sudo reboot

    sudo mount -o remount,ro /
    sudo mount -o remount,ro /root_bypass_ramdisks
	fi
}

connect "${1}"

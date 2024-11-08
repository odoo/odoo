#!/usr/bin/env bash

set_brightness() {
    echo "${1}" > /sys/class/leds/led0/brightness
}

check_status_loop() {
    while true ; do
	if wget --quiet localhost:8069/hw_proxy/hello -O /dev/null ; then
	    set_brightness 255
	else
	    set_brightness 0
	fi
        sleep 5
    done
}

echo none > /sys/class/leds/led0/trigger
check_status_loop

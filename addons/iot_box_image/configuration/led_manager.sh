#!/bin/bash

STATUS_UPDATE_DELAY_SECONDS=10
BLINK_DELAY_SECONDS=1

IS_PI5=false
if grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
    IS_PI5=true
fi

LED_ACT="/sys/class/leds/ACT"
LED_PWR="/sys/class/leds/PWR"

# Disable default LED triggers (so we control them manually)
echo none > "$LED_ACT/trigger"
echo none > "$LED_PWR/trigger"

# Define ON/OFF constant values based on model
if $IS_PI5; then
    ACT_ON=0   # Inverted logic on Pi5
    ACT_OFF=1
else
    ACT_ON=1
    ACT_OFF=0
fi
PWR_ON=1
PWR_OFF=0

set_leds() {
    echo "$1" > "$LED_ACT/brightness"
    echo "$2" > "$LED_PWR/brightness"
}

while true; do
    if systemctl is-active --quiet hostapd; then
        # AP mode: Red ON, Green OFF
        set_leds "$ACT_OFF" "$PWR_ON"
        sleep $STATUS_UPDATE_DELAY_SECONDS
        continue
    fi

    if ! ping -q -c 1 -W 2 1.1.1.1 >/dev/null; then
        # No network: Red ON, Green OFF
        set_leds "$ACT_OFF" "$PWR_ON"
        sleep $STATUS_UPDATE_DELAY_SECONDS
        continue
    fi

    if grep -q "remote_server" /home/pi/odoo.conf 2>/dev/null; then
        # Paired with database: Green ON, Red OFF
        set_leds "$ACT_ON" "$PWR_OFF"
        sleep $STATUS_UPDATE_DELAY_SECONDS
    else
        # Not paired: blink green LED (red stays off)
        for i in {1..10}; do
            # Toggle green every second
            if (( i % 2 == 1 )); then
                echo "$ACT_ON" > "$LED_ACT/brightness"
            else
                echo "$ACT_OFF" > "$LED_ACT/brightness"
            fi
            # Ensure red LED remains OFF
            echo "$PWR_OFF" > "$LED_PWR/brightness"
            sleep $BLINK_DELAY_SECONDS
        done
    fi
done

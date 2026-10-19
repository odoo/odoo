#!/bin/bash

STATUS_UPDATE_DELAY_SECONDS=10

GREEN_LED="/sys/class/leds/ACT/trigger"
RED_LED="/sys/class/leds/PWR/trigger"
TEST_FLAG="/tmp_ram/led_manager_test"

IS_PI5=false
if grep -q "Raspberry Pi 5" /proc/device-tree/model 2>/dev/null; then
    IS_PI5=true
fi

led_off() {
    if $IS_PI5 && [ "$1" == "$GREEN_LED" ]; then
        echo "default-on" > "$1"
    else
        echo "none" > "$1"
    fi
}

led_constant() {
    if $IS_PI5 && [ "$1" == "$GREEN_LED" ]; then
        echo "none" > "$1"
    else
        echo "default-on" > "$1"
    fi
}

led_blink() {
    echo "heartbeat" > "$1"
}

led_test() {
    echo "timer" > "$1"
    sleep 0.5
    echo "timer" > "$2"
}

# Disable both LEDs initially
led_off "$GREEN_LED"
led_off "$RED_LED"

while true; do
    # Test mode: blink red and green LEDs for 30 seconds, then continue normal operation
    if [ -f "$TEST_FLAG" ]; then
        rm -f "$TEST_FLAG"
        led_test "$GREEN_LED" "$RED_LED"
        sleep 30
        continue
    fi
    sleep $STATUS_UPDATE_DELAY_SECONDS
    if ! ping -q -c 1 -W 2 1.1.1.1 >/dev/null; then
        # No network: blink red LED, (green stays off)
        led_blink "$RED_LED"
        led_off "$GREEN_LED"
        continue
    fi

    if ! systemctl is-active --quiet odoo.service; then
        # Odoo service is not running: Red ON, Green OFF
        led_constant "$RED_LED"
        led_off "$GREEN_LED"
        continue
    fi

    if grep -q "remote_server" /home/pi/odoo.conf 2>/dev/null; then
        # Paired with database: Green ON, Red OFF
        led_constant "$GREEN_LED"
        led_off "$RED_LED"
    else
        # Not paired: blink green LED (red stays off)
        led_blink "$GREEN_LED"
        led_off "$RED_LED"
    fi
done

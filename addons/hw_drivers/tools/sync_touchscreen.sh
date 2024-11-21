#!/usr/bin/env bash

if [ $# -eq 0 ]; then
    echo "No output screen specified, assuming :0.0"
    screen=1
else
    screen="$1"
fi

# Get touchscreen name
touchscreen_name=$(udevadm info --export-db | awk '/ID_INPUT_TOUCHSCREEN=1/' RS= | grep "^E: NAME=" | cut -d '"' -f2)
if [ -z "$touchscreen_name" ]; then
    echo "No touchscreen found"
    exit 1
fi

# Get touchscreen device ids (Elo Touchscreen appears twice in the list)
device_id_0=$(xinput list | grep "$touchscreen_name" | head -1 | cut -d "=" -f2 | cut -d$'\t' -f1)
device_id_1=$(xinput list | grep "$touchscreen_name" | tail -1 | cut -d "=" -f2 | cut -d$'\t' -f1)

# Get screen name: default will return the 1st line (e.g. HDMI-1)
output_name=$(xrandr --listactivemonitors | awk '{print $NF}' | tail -n +2 | awk -v screen="$screen" 'NR==screen')

# Map touchscreen matrix to screen configuration (orientation)
xinput map-to-output $device_id_0 "$output_name"
xinput map-to-output $device_id_1 "$output_name"

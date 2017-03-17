#!/usr/bin/env bash

make_browser_fullscreen () {
    # wait until the browser window exists
    while ! xdotool search --onlyvisible chromium 2> /dev/null ; do
        sleep 1
    done

    # wait some more because just because xdotool finds it doesn't
    # mean it's ready to be resized
    sleep 2

    # Newer versions of xdotool (eg. 3.20) support specifying windowsize
    # as a percentage of the total resolution. So with those we could just
    # set the windowsize to 100% 100%. But wheezy comes with an ancient
    # version of xdotool which does not support this. So we have to figure
    # out the resolution ourselves.
    RESOLUTION=$(xrandr | grep '\*' | grep -o '[0-9]\+x[0-9]\+')
    RESOLUTION_WIDTH=$(echo "${RESOLUTION}" | grep -o '^.*x' | sed s/x//)
    RESOLUTION_HEIGHT=$(echo "${RESOLUTION}" | grep -o 'x.*$' | sed s/x//)

    logger -t posbox_startup_x "setting chromium window to ${RESOLUTION_WIDTH}x${RESOLUTION_HEIGHT}"

    xdotool search --onlyvisible chromium windowsize "${RESOLUTION_WIDTH}" "${RESOLUTION_HEIGHT}"
}

make_browser_fullscreen &

# hide cursor
unclutter -idle 1 &

# don't powersave on monitor
xset s off     # don't activate screensaver
xset -dpms     # disable DPMS (Energy Star) features.
xset s noblank # don't blank the video device

# chromium wants to write in home, we don't want to create a ramdisk
# for it so just redefine home
HOME="/tmp"
chromium-browser --remote-debugging-port=9222 --disable-translate --kiosk /home/pi/odoo/addons/point_of_sale/tools/posbox/configuration/initial_customer_facing_display.html

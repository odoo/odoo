import platform
import subprocess
import time
from threading import Thread, Timer
from odoo.addons.hw_drivers.tools import helpers, wifi

STATUS_UPDATE_DELAY_SECONDS = 10.0
BLINK_DELAY_SECONDS = 1.0

class LedManager(Thread):
    daemon = True

    def __init__(self):
        super().__init__()
        self.green_led_on = None
        self.red_led_on = None
        self.blinking = False

    def run(self):
        self._disable_led_triggers()

        while True:
            if wifi.is_access_point() or not helpers.get_ip():
                # RED if there is no internet
                self._set_leds("red")
            elif helpers.get_odoo_server_url():
                # GREEN if there is internet and connected to DB
                self._set_leds("green")
            else:
                # BLINKING GREEN there is internet but not yet paired
                self._set_leds("blinking")
            time.sleep(STATUS_UPDATE_DELAY_SECONDS)

    def _disable_led_triggers(self):
        subprocess.run(["sudo", "tee", "/sys/class/leds/ACT/trigger"], input="none", text=True)
        subprocess.run(["sudo", "tee", "/sys/class/leds/PWR/trigger"], input="none", text=True)

    def _set_green_led(self, value):
        if self.green_led_on == value:
            return
        self.green_led_on = value
        if helpers.raspberry_pi_model == 5:
            # 'ACT' LED is inverted on Raspberry Pi 5
            value = not value
        subprocess.run(["sudo", "tee", "/sys/class/leds/ACT/brightness"], input="1" if value else "0", text=True)

    def _set_red_led(self, value):
        if self.red_led_on == value:
            return
        self.red_led_on = value
        subprocess.run(["sudo", "tee", "/sys/class/leds/PWR/brightness"], input="1" if value else "0", text=True)

    def _blink_green_led(self):
        if not self.blinking:
            return
        self._set_green_led(not self.green_led_on)
        Timer(BLINK_DELAY_SECONDS, self._blink_green_led).start()

    def _set_leds(self, value):
        self._set_red_led(value == "red")
        if value == "blinking":
            if not self.blinking:
                self.blinking = True
                self._blink_green_led()
        else:
            self.blinking = False
            self._set_green_led(value == "green")


if platform.system() == 'Linux':
    led_manager = LedManager()
    led_manager.start()

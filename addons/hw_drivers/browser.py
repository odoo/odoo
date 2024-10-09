# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import subprocess
from enum import Enum
from odoo.addons.hw_drivers.tools import helpers


_logger = logging.getLogger(__name__)
MIN_IMAGE_VERSION = 24.08


class BrowserState(Enum):
    """Enum to represent the state of the browser"""
    NORMAL = 'normal'
    KIOSK = 'kiosk'
    FULLSCREEN = 'fullscreen'


class Browser:
    """Methods to interact with a browser"""

    def __init__(self, url, _x_screen, env, kiosk=False):
        """
        :param url: URL to open in the browser
        :param _x_screen: X screen number
        :param env: Environment variables (e.g. os.environ.copy())
        :param kiosk: Whether the browser should be in kiosk mode
        """
        self.url = url
        # helpers.get_version returns a string formatted as: <L|W><version> (L: Linux, W: Windows)
        self.browser = 'chromium-browser' if float(helpers.get_version()[1:]) >= MIN_IMAGE_VERSION else 'firefox'
        self.browser_process_name = 'chromium' if self.browser == 'chromium-browser' else self.browser
        self._x_screen = _x_screen
        self._set_environment(env)
        self.kiosk_args = [
            '--kiosk',
            '--incognito',
            '--disable-infobars',
            '--noerrdialogs',
            '--no-first-run',
        ]
        self.fullscreen_args = ['--start-fullscreen']
        self.chromium_additional_args = [
            '--bwsi',  # Use Chromium without signing in
            '--disable-extensions',  # disable extensions as they fill up /tmp
            *(self.kiosk_args if kiosk else [])
        ]

    def _set_environment(self, env):
        """
        Set the environment variables for the browser
        :param env: Environment variables (os.environ.copy())
        """
        self.env = env
        self.env['DISPLAY'] = f':0.{self._x_screen}'
        self.env['XAUTHORITY'] = '/run/lightdm/pi/xauthority'
        for key in ['HOME', 'XDG_RUNTIME_DIR', 'XDG_CACHE_HOME']:
            self.env[key] = '/tmp/' + self._x_screen

    def open_browser(self, url=None, state=BrowserState.NORMAL):
        """
        open the browser with the given URL, or reopen it if it is already open
        :param url: URL to open in the browser
        :param state: State of the browser (normal, kiosk, fullscreen)
        :return: Browser instance (subprocess.Popen instance)
        """
        self.url = url or self.url

        # Reopen to take new url or additional args into account
        self.close_browser()

        if state == BrowserState.KIOSK:
            self.enable_kiosk_mode()
        elif state == BrowserState.FULLSCREEN:
            self.fullscreen()

        subprocess.Popen(
            [
                self.browser,
                self.url,
                '--disk-cache-dir=/dev/null',   # Disable disk cache
                '--disk-cache-size=1',          # Set disk cache size to 1 byte
                '--log-level=3',                # Reduce amount of logs
                *self.chromium_additional_args,
            ],
            env=self.env,
        )
        helpers.save_browser_state(url=self.url)

    def close_browser(self):
        """close the browser"""
        # Kill browser instance (can't `instance.pkill()` as we can't keep the instance after Odoo service restarts)
        # We need to terminate it because Odoo will create a new instance each time it is restarted.
        subprocess.run(['pkill', self.browser_process_name], check=False)

    def xdotool_keystroke(self, keystroke):
        """
        Execute a keystroke using xdotool
        :param keystroke: Keystroke to execute
        """
        subprocess.run([
            'xdotool', 'search',
            '--sync', '--onlyvisible',
            '--screen', self._x_screen,
            '--class', self.browser_process_name,
            'key', keystroke,
        ], check=False)

    def xdotool_type(self, text):
        """
        Type text using xdotool
        :param text: Text to type
        """
        subprocess.run([
            'xdotool', 'search',
            '--sync', '--onlyvisible',
            '--screen', self._x_screen,
            '--class', self.browser_process_name,
            'type', text,
        ], check=False)

    def open_new_tab(self, url):
        """
        Open a new tab with the given URL
        :param url: URL to open in the new tab
        """
        self.url = url
        self.xdotool_keystroke('ctrl+t')
        self.xdotool_type(self.url)
        self.xdotool_keystroke('Return')

    def refresh(self):
        """Refresh the current tab"""
        self.xdotool_keystroke('ctrl+r')

    def fullscreen(self):
        """Adds required arguments to chromium-browser cli to open it """
        self.chromium_additional_args = self.fullscreen_args

    def enable_kiosk_mode(self):
        """Adds required arguments to chromium-browser cli to open it in kiosk mode"""
        self.chromium_additional_args = self.kiosk_args

    def disable_kiosk_mode(self):
        """Removes arguments to chromium-browser cli to open it without kiosk mode"""
        if '--kiosk' in self.chromium_additional_args:
            self.chromium_additional_args = [arg for arg in self.chromium_additional_args if arg not in self.kiosk_args]
            self.open_browser()

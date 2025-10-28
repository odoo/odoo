# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import subprocess
from enum import Enum
from odoo.addons.iot_drivers.tools import helpers


_logger = logging.getLogger(__name__)

CHROMIUM_ARGS = [
    '--incognito',
    '--disable-infobars',
    '--noerrdialogs',
    '--no-first-run',
    '--bwsi',                       # Use chromium without signing in
    '--disable-extensions',         # Disable extensions as they fill up /tmp
    '--disk-cache-dir=/dev/null',   # Disable disk cache
    '--disk-cache-size=1',          # Set disk cache size to 1 byte
    '--log-level=3',                # Reduce amount of logs
]


class BrowserState(Enum):
    """Enum to represent the state of the browser"""
    NORMAL = 'normal'
    KIOSK = 'kiosk'
    FULLSCREEN = 'fullscreen'


class Browser:
    """Methods to interact with a browser"""

    def __init__(self, url, _x_screen, env):
        """
        :param url: URL to open in the browser
        :param _x_screen: X screen number
        :param env: Environment variables (e.g. os.environ.copy())
        :param kiosk: Whether the browser should be in kiosk mode
        """
        self.url = url
        self.browser = 'chromium'
        self.state = BrowserState.NORMAL
        self._x_screen = _x_screen
        self._set_environment(env)
        self.open_browser()

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

    def open_browser(self, url=None, state=BrowserState.FULLSCREEN):
        """
        open the browser with the given URL, or reopen it if it is already open
        :param url: URL to open in the browser
        :param state: State of the browser (normal, kiosk, fullscreen)
        """
        self.url = url or self.url
        self.state = state

        # Reopen to take new url or additional args into account
        self.close_browser()

        browser_args = list(CHROMIUM_ARGS)

        if state == BrowserState.KIOSK:
            browser_args.extend(["--kiosk", "--touch-events"])
        elif state == BrowserState.FULLSCREEN:
            browser_args.append("--start-fullscreen")

        subprocess.Popen(
            [
                self.browser,
                self.url,
                *browser_args,
            ],
            env=self.env,
        )

        helpers.save_browser_state(url=self.url)

    def close_browser(self):
        """close the browser"""
        # Kill browser instance (can't `instance.pkill()` as we can't keep the instance after Odoo service restarts)
        # We need to terminate it because Odoo will create a new instance each time it is restarted.
        subprocess.run(['pkill', self.browser], check=False)

    def xdotool_keystroke(self, keystroke):
        """
        Execute a keystroke using xdotool
        :param keystroke: Keystroke to execute
        """
        subprocess.run([
            'xdotool', 'search',
            '--sync', '--onlyvisible',
            '--screen', self._x_screen,
            '--class', self.browser,
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
            '--class', self.browser,
            'type', text,
        ], check=False)

    def refresh(self):
        """Refresh the current tab"""
        self.xdotool_keystroke('ctrl+r')

    def disable_kiosk_mode(self):
        """Removes arguments to chromium-browser cli to open it without kiosk mode"""
        if self.state == BrowserState.KIOSK:
            self.open_browser(state=BrowserState.FULLSCREEN)

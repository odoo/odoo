# Part of Odoo. See LICENSE file for full copyright and licensing details.
import subprocess


class Browser:
    """Methods to interact with a browser"""

    def __init__(self, url, _x_screen, env=None, kiosk=False):
        """
        :param url: URL to open in the browser
        :param _x_screen: X screen number
        :param env: Environment variables
        :param kiosk: Whether the browser should be in kiosk mode
        """
        self.url = url
        self.browser = 'chromium-browser'
        self._x_screen = _x_screen
        self.env = env
        self.env['HOME'] = '/tmp/' + self._x_screen
        self.kiosk_args = [
            '--kiosk',
            '--incognito',
            '--disable-infobars',
            '--noerrdialogs',
            '--no-first-run',
        ]
        self.chromium_additional_args = self.kiosk_args if kiosk else []

        self.instance = None

    def open_browser(self, url=None):
        """open the browser with the given URL, or reopen it if it is already open"""
        self.url = url or self.url

        # Reopen to take new url or additional args into account
        if self.instance:
            self.close_browser()

        self.instance = subprocess.Popen(
            [
                self.browser,
                self.url,
                '--disk-cache-dir=/dev/null',
                '--disk-cache-size=1',
                *self.chromium_additional_args,
            ],
            env=self.env,
            stdout=subprocess.DEVNULL,  # Chromium logs a lot of stuff, avoid contaminating Odoo logs
            stderr=subprocess.DEVNULL,
        )
        return self.instance

    def close_browser(self):
        """close the browser"""
        subprocess.run(['pkill', self.browser.split('-')[0] + '*'], check=False)
        subprocess.run(['rm', '-rf', f'/tmp/{self._x_screen}/.cache'], check=False)  # Remove cached files to free space
        self.instance = None

    def xdotool_keystroke(self, keystroke):
        """Execute a keystroke using xdotool"""
        try:
            subprocess.call([
                'xdotool', 'search',
                '--sync', '--onlyvisible',
                '--screen', self._x_screen,
                '--class', self.browser.capitalize(),
                'key', keystroke,
            ])
            return "xdotool succeeded in stroking " + keystroke
        except subprocess.SubprocessError:
            return "xdotool failed in stroking " + keystroke

    def xdotool_type(self, text):
        """Type text using xdotool"""
        try:
            subprocess.call([
                'xdotool', 'search',
                '--sync', '--onlyvisible',
                '--screen', self._x_screen,
                '--class', self.browser.capitalize(),
                'type', text,
            ])
            return "xdotool succeeded in typing " + text
        except subprocess.SubprocessError:
            return "xdotool failed in typing " + text

    def open_new_tab(self, url):
        """Open a new tab with the given URL"""
        self.url = url
        self.xdotool_keystroke('ctrl+t')
        self.xdotool_type(self.url)
        self.xdotool_keystroke('Return')

    def fullscreen(self):
        """Make the browser fullscreen"""
        self.chromium_additional_args = ['--start-fullscreen']
        self.open_browser()

    def refresh(self):
        """Refresh the current tab"""
        self.xdotool_keystroke('ctrl+r')

    def enable_kiosk_mode(self):
        """Enable kiosk mode in browser with the given orientation"""
        if not self.is_kiosk():
            self.chromium_additional_args.extend(self.kiosk_args)
            self.open_browser()

    def disable_kiosk_mode(self):
        """Disable kiosk mode in browser"""
        if self.is_kiosk():
            self.chromium_additional_args = [arg for arg in self.chromium_additional_args if arg not in self.kiosk_args]
            self.open_browser()

    def is_kiosk(self):
        return '--kiosk' in self.chromium_additional_args

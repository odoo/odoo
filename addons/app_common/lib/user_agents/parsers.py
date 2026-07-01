from collections import namedtuple

from ..ua_parser import user_agent_parser
from .compat import string_types


MOBILE_DEVICE_FAMILIES = (
    'iPhone',
    'iPod',
    'Generic Smartphone',
    'Generic Feature Phone',
    'PlayStation Vita',
    'iOS-Device'
)

PC_OS_FAMILIES = (
    'Windows 95',
    'Windows 98',
    'Solaris',
)

MOBILE_OS_FAMILIES = (
    'Windows Phone',
    'Windows Phone OS',  # Earlier versions of ua-parser returns Windows Phone OS
    'Symbian OS',
    'Bada',
    'Windows CE',
    'Windows Mobile',
    'Maemo',
)

MOBILE_BROWSER_FAMILIES = (
    'IE Mobile',
    'Opera Mobile',
    'Opera Mini',
    'Chrome Mobile',
    'Chrome Mobile WebView',
    'Chrome Mobile iOS',
)

TABLET_DEVICE_FAMILIES = (
    'iPad',
    'BlackBerry Playbook',
    'Blackberry Playbook',  # Earlier versions of ua-parser returns "Blackberry" instead of "BlackBerry"
    'Kindle',
    'Kindle Fire',
    'Kindle Fire HD',
    'Galaxy Tab',
    'Xoom',
    'Dell Streak',
)

TOUCH_CAPABLE_OS_FAMILIES = (
    'iOS',
    'Android',
    'Windows Phone',
    'Windows CE',
    'Windows Mobile',
    'Firefox OS',
    'MeeGo',
)

TOUCH_CAPABLE_DEVICE_FAMILIES = (
    'BlackBerry Playbook',
    'Blackberry Playbook',
    'Kindle Fire',
)

EMAIL_PROGRAM_FAMILIES = set((
    'Outlook',
    'Windows Live Mail',
    'AirMail',
    'Apple Mail',
    'Outlook',
    'Thunderbird',
    'Lightning',
    'ThunderBrowse',
    'Windows Live Mail',
    'The Bat!',
    'Lotus Notes',
    'IBM Notes',
    'Barca',
    'MailBar',
    'kmail2',
    'YahooMobileMail'
))

def verify_attribute(attribute):
    if isinstance(attribute, string_types) and attribute.isdigit():
        return int(attribute)

    return attribute


def parse_version(major=None, minor=None, patch=None, patch_minor=None):
    # Returns version number tuple, attributes will be integer if they're numbers
    major = verify_attribute(major)
    minor = verify_attribute(minor)
    patch = verify_attribute(patch)
    patch_minor = verify_attribute(patch_minor)

    return tuple(
        filter(lambda x: x is not None, (major, minor, patch, patch_minor))
    )


Browser = namedtuple('Browser', ['family', 'version', 'version_string'])


def parse_browser(family, major=None, minor=None, patch=None, patch_minor=None):
    # Returns a browser object
    version = parse_version(major, minor, patch)
    version_string = '.'.join([str(v) for v in version])
    return Browser(family, version, version_string)


OperatingSystem = namedtuple('OperatingSystem', ['family', 'version', 'version_string'])


def parse_operating_system(family, major=None, minor=None, patch=None, patch_minor=None):
    version = parse_version(major, minor, patch)
    version_string = '.'.join([str(v) for v in version])
    return OperatingSystem(family, version, version_string)


Device = namedtuple('Device', ['family', 'brand', 'model'])


def parse_device(family, brand, model):
    return Device(family, brand, model)


class UserAgent(object):

    def __init__(self, user_agent_string):
        ua_dict = user_agent_parser.Parse(user_agent_string)
        self.ua_string = user_agent_string
        self.os = parse_operating_system(**ua_dict['os'])
        self.browser = parse_browser(**ua_dict['user_agent'])
        self.device = parse_device(**ua_dict['device'])

    def __str__(self):
        return "{device} / {os} / {browser}".format(
            device=self.get_device(),
            os=self.get_os(),
            browser=self.get_browser()
        )

    def __unicode__(self):
        return unicode(str(self))

    def _is_android_tablet(self):
        # Newer Android tablets don't have "Mobile" in their user agent string,
        # older ones like Galaxy Tab still have "Mobile" though they're not
        if ('Mobile Safari' not in self.ua_string and
                self.browser.family != "Firefox Mobile"):
            return True
        return False

    def _is_blackberry_touch_capable_device(self):
        # A helper to determine whether a BB phone has touch capabilities
        # Blackberry Bold Touch series begins with 99XX
        if 'Blackberry 99' in self.device.family:
            return True
        if 'Blackberry 95' in self.device.family:  # BB Storm devices
            return True
        return False

    def get_device(self):
        return self.is_pc and "PC" or self.device.family

    def get_os(self):
        return ("%s %s" % (self.os.family, self.os.version_string)).strip()

    def get_browser(self):
        return ("%s %s" % (self.browser.family, self.browser.version_string)).strip()

    @property
    def is_tablet(self):
        if self.device.family in TABLET_DEVICE_FAMILIES:
            return True
        if (self.os.family == 'Android' and self._is_android_tablet()):
            return True
        if self.os.family == 'Windows' and self.os.version_string.startswith('RT'):
            return True
        if self.os.family == 'Firefox OS' and 'Mobile' not in self.browser.family:
            return True
        return False

    @property
    def is_mobile(self):
        # First check for mobile device and mobile browser families
        if self.device.family in MOBILE_DEVICE_FAMILIES:
            return True
        if self.browser.family in MOBILE_BROWSER_FAMILIES:
            return True
        # Device is considered Mobile OS is Android and not tablet
        # This is not fool proof but would have to suffice for now
        if ((self.os.family == 'Android' or self.os.family == 'Firefox OS')
            and not self.is_tablet):
            return True
        if self.os.family == 'BlackBerry OS' and self.device.family != 'Blackberry Playbook':
            return True
        if self.os.family in MOBILE_OS_FAMILIES:
            return True
        # TODO: remove after https://github.com/tobie/ua-parser/issues/126 is closed
        if 'J2ME' in self.ua_string or 'MIDP' in self.ua_string:
            return True
        # This is here mainly to detect Google's Mobile Spider
        if 'iPhone;' in self.ua_string:
            return True
        if 'Googlebot-Mobile' in self.ua_string:
            return True
        # Mobile Spiders should be identified as mobile
        if self.device.family == 'Spider' and 'Mobile' in self.browser.family:
            return True
        # Nokia mobile
        if 'NokiaBrowser' in self.ua_string and 'Mobile' in self.ua_string:
            return True
        return False

    @property
    def is_touch_capable(self):
        # TODO: detect touch capable Nokia devices
        if self.os.family in TOUCH_CAPABLE_OS_FAMILIES:
            return True
        if self.device.family in TOUCH_CAPABLE_DEVICE_FAMILIES:
            return True
        if self.os.family == 'Windows':
            if self.os.version_string.startswith(('RT', 'CE')):
                return True
            if self.os.version_string.startswith('8') and 'Touch' in self.ua_string:
                return True
        if 'BlackBerry' in self.os.family and self._is_blackberry_touch_capable_device():
            return True
        return False

    @property
    def is_pc(self):
        # Returns True for "PC" devices (Windows, Mac and Linux)
        if 'Windows NT' in self.ua_string or self.os.family in PC_OS_FAMILIES or \
           self.os.family == 'Windows' and self.os.version_string == 'ME':
            return True
        # TODO: remove after https://github.com/tobie/ua-parser/issues/127 is closed
        if self.os.family == 'Mac OS X' and 'Silk' not in self.ua_string:
            return True
        # Maemo has 'Linux' and 'X11' in UA, but it is not for PC
        if 'Maemo' in self.ua_string:
            return False
        if 'Chrome OS' in self.os.family:
            return True
        if 'Linux' in self.ua_string and 'X11' in self.ua_string:
            return True
        return False

    @property
    def is_bot(self):
        return True if self.device.family == 'Spider' else False

    @property
    def is_email_client(self):
        if self.browser.family in EMAIL_PROGRAM_FAMILIES:
            return True
        return False


def parse(user_agent_string):
    return UserAgent(user_agent_string)

"""
User agent string parser.

Originally from werkzeug.useragents (removed in werkzeug 2.1).
Vendored to preserve browser/platform detection that werkzeug dropped.

:copyright: 2007 Pallets
:license: BSD-3-Clause
"""

import re


class UserAgentParser:
    """A simple user agent parser.  Used by the `UserAgent`."""

    platforms = (
        ("cros", "chromeos"),
        ("iphone|ios", "iphone"),
        ("ipad", "ipad"),
        (r"darwin|mac|os\s*x", "macos"),
        ("win", "windows"),
        (r"android", "android"),
        ("netbsd", "netbsd"),
        ("openbsd", "openbsd"),
        ("freebsd", "freebsd"),
        ("dragonfly", "dragonflybsd"),
        ("(sun|i86)os", "solaris"),
        (r"x11|lin(\b|ux)?", "linux"),
        (r"nintendo\s+wii", "wii"),
        ("irix", "irix"),
        ("hp-?ux", "hpux"),
        ("aix", "aix"),
        ("sco|unix_sv", "sco"),
        ("bsd", "bsd"),
        ("amiga", "amiga"),
        ("blackberry|playbook", "blackberry"),
        ("symbian", "symbian"),
    )
    browsers = (
        ("googlebot", "google"),
        ("msnbot", "msn"),
        ("yahoo", "yahoo"),
        ("ask jeeves", "ask"),
        (r"aol|america\s+online\s+browser", "aol"),
        ("opera", "opera"),
        ("edge", "edge"),
        ("chrome|crios", "chrome"),
        ("seamonkey", "seamonkey"),
        ("firefox|firebird|phoenix|iceweasel", "firefox"),
        ("galeon", "galeon"),
        ("safari|version", "safari"),
        ("webkit", "webkit"),
        ("camino", "camino"),
        ("konqueror", "konqueror"),
        ("k-meleon", "kmeleon"),
        ("netscape", "netscape"),
        (r"msie|microsoft\s+internet\s+explorer|trident/.+? rv:", "msie"),
        ("lynx", "lynx"),
        ("links", "links"),
        ("Baiduspider", "baidu"),
        ("bingbot", "bing"),
        ("mozilla", "mozilla"),
    )

    _browser_version_re = r"(?:%s)[/\sa-z(]*(\d+[.\da-z]+)?"
    _language_re = re.compile(
        r"(?:;\s*|\s+)(\b\w{2}\b(?:-\b\w{2}\b)?)\s*;|"
        r"(?:\(|\[|;)\s*(\b\w{2}\b(?:-\b\w{2}\b)?)\s*(?:\]|\)|;)"
    )

    def __init__(self):
        self.platforms = tuple((b, re.compile(a, re.I)) for a, b in self.platforms)
        self.browsers = tuple(
            (b, re.compile(self._browser_version_re % a, re.I))
            for a, b in self.browsers
        )

    def __call__(self, user_agent):
        for platform, regex in self.platforms:  # noqa: B007
            match = regex.search(user_agent)
            if match is not None:
                break
        else:
            platform = None
        for browser, regex in self.browsers:  # noqa: B007
            match = regex.search(user_agent)
            if match is not None:
                version = match.group(1)
                break
        else:
            browser = version = None
        match = self._language_re.search(user_agent)
        if match is not None:
            language = match.group(1) or match.group(2)
        else:
            language = None
        return platform, browser, version, language


class UserAgent:
    """Represents a parsed user agent string.

    Attributes:
        string: the raw user agent string
        platform: detected OS platform (e.g. 'linux', 'windows', 'macos')
        browser: detected browser name (e.g. 'chrome', 'firefox', 'safari')
        version: detected browser version string
        language: detected language code (e.g. 'en-US')
    """

    _parser = UserAgentParser()

    def __init__(self, environ_or_string):
        if isinstance(environ_or_string, dict):
            environ_or_string = environ_or_string.get("HTTP_USER_AGENT", "")
        self.string = environ_or_string
        self.platform, self.browser, self.version, self.language = self._parser(
            environ_or_string
        )

    def to_header(self):
        return self.string

    def __str__(self):
        return self.string

    def __bool__(self):
        return bool(self.browser)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.browser!r}/{self.version}>"

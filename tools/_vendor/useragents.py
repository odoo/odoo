# -*- coding: utf-8 -*-
"""
    werkzeug.useragents
    ~~~~~~~~~~~~~~~~~~~

    This module provides a helper to inspect user agent strings.  This module
    is far from complete but should work for most of the currently available
    browsers.


    :copyright: 2007 Pallets
    :license: BSD-3-Clause

    This package was vendored in odoo in order to prevent errors with werkzeug 2.1
"""
import re


class UserAgentParser(object):
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
        self.platforms = [(b, re.compile(a, re.I)) for a, b in self.platforms]
        self.browsers = [
            (b, re.compile(self._browser_version_re % a, re.I))
            for a, b in self.browsers
        ]

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


class UserAgent(object):
    """Represents a user agent.  Pass it a WSGI environment or a user agent
    string and you can inspect some of the details from the user agent
    string via the attributes.  The following attributes exist:

    .. attribute:: string

       the raw user agent string

    .. attribute:: platform

       the browser platform.  The following platforms are currently
       recognized:

       -   `aix`
       -   `amiga`
       -   `android`
       -   `blackberry`
       -   `bsd`
       -   `chromeos`
       -   `dragonflybsd`
       -   `freebsd`
       -   `hpux`
       -   `ipad`
       -   `iphone`
       -   `irix`
       -   `linux`
       -   `macos`
       -   `netbsd`
       -   `openbsd`
       -   `sco`
       -   `solaris`
       -   `symbian`
       -   `wii`
       -   `windows`

    .. attribute:: browser

        the name of the browser.  The following browsers are currently
        recognized:

        -   `aol` *
        -   `ask` *
        -   `baidu` *
        -   `bing` *
        -   `camino`
        -   `chrome`
        -   `edge`
        -   `firefox`
        -   `galeon`
        -   `google` *
        -   `kmeleon`
        -   `konqueror`
        -   `links`
        -   `lynx`
        -   `mozilla`
        -   `msie`
        -   `msn`
        -   `netscape`
        -   `opera`
        -   `safari`
        -   `seamonkey`
        -   `webkit`
        -   `yahoo` *

        (Browsers marked with a star (``*``) are crawlers.)

    .. attribute:: version

        the version of the browser

    .. attribute:: language

        the language of the browser
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

    def __nonzero__(self):
        return bool(self.browser)

    __bool__ = __nonzero__

    def __repr__(self):
        return "<%s %r/%s>" % (self.__class__.__name__, self.browser, self.version)

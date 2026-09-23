import functools
import re


class UserAgentParser:

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

    def __init__(self) -> None:
        self.platforms = tuple(
            (b, re.compile(a, re.IGNORECASE)) for a, b in self.platforms
        )
        self.browsers = tuple(
            (b, re.compile(self._browser_version_re % a, re.IGNORECASE))
            for a, b in self.browsers
        )
        self._parse_cached = functools.lru_cache(maxsize=2048)(self._parse)

    def __call__(
        self, user_agent: str
    ) -> tuple[str | None, str | None, str | None, str | None]:
        return self._parse_cached(user_agent)

    def _parse(
        self, user_agent: str
    ) -> tuple[str | None, str | None, str | None, str | None]:
        for platform, regex in self.platforms:
            match = regex.search(user_agent)
            if match is not None:
                break
        else:
            platform = None
        for browser, regex in self.browsers:
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

    _parser = UserAgentParser()

    def __init__(self, environ_or_string: dict[str, str] | str) -> None:
        if isinstance(environ_or_string, dict):
            environ_or_string = environ_or_string.get("HTTP_USER_AGENT", "")
        self.string = environ_or_string
        self.platform, self.browser, self.version, self.language = self._parser(
            environ_or_string
        )

    def to_header(self) -> str:
        return self.string

    def __str__(self) -> str:
        return self.string

    def __bool__(self) -> bool:
        return bool(self.browser)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} {self.browser!r}/{self.version}>"

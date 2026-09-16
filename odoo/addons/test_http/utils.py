from html.parser import HTMLParser

import geoip2.errors
import geoip2.models

from odoo.http import MemorySessionStore as _MemorySessionStore

TEST_IP = "192.0.2.42"
TEST_IP_GEOIP_CITY = geoip2.models.City(
    ["en"],
    continent={
        "code": "EU",
        "geoname_id": 6255148,
        "names": {
            "de": "Europa",
            "en": "Europe",
            "es": "Europa",
            "fr": "Europe",
            "ja": "ヨーロッパ",
            "pt-BR": "Europa",
            "ru": "Европа",
            "zh-CN": "欧洲",
        },
    },
    country={
        "geoname_id": 3017382,
        "is_in_european_union": True,
        "iso_code": "FR",
        "names": {
            "de": "Frankreich",
            "en": "France",
            "es": "Francia",
            "fr": "France",
            "ja": "フランス共和国",
            "pt-BR": "França",
            "ru": "Франция",
            "zh-CN": "法国",
        },
    },
    location={
        "accuracy_radius": 500,
        "latitude": 48.8582,
        "longitude": 2.3387,
        "time_zone": "Europe/Paris",
    },
    registered_country={
        "geoname_id": 3017382,
        "is_in_european_union": True,
        "iso_code": "FR",
        "names": {
            "de": "Frankreich",
            "en": "France",
            "es": "Francia",
            "fr": "France",
            "ja": "フランス共和国",
            "pt-BR": "França",
            "ru": "Франция",
            "zh-CN": "法国",
        },
    },
    traits={"ip_address": TEST_IP, "prefix_len": 21},
)
TEST_IP_GEOIP_COUNTRY = geoip2.models.Country(
    ["en"],
    continent={
        "code": "EU",
        "geoname_id": 6255148,
        "names": {
            "de": "Europa",
            "en": "Europe",
            "es": "Europa",
            "fr": "Europe",
            "ja": "ヨーロッパ",
            "pt-BR": "Europa",
            "ru": "Европа",
            "zh-CN": "欧洲",
        },
    },
    country={
        "geoname_id": 3017382,
        "is_in_european_union": True,
        "iso_code": "FR",
        "names": {
            "de": "Frankreich",
            "en": "France",
            "es": "Francia",
            "fr": "France",
            "ja": "フランス共和国",
            "pt-BR": "França",
            "ru": "Франция",
            "zh-CN": "法国",
        },
    },
    registered_country={
        "geoname_id": 3017382,
        "is_in_european_union": True,
        "iso_code": "FR",
        "names": {
            "de": "Frankreich",
            "en": "France",
            "es": "Francia",
            "fr": "France",
            "ja": "フランス共和国",
            "pt-BR": "França",
            "ru": "Франция",
            "zh-CN": "法国",
        },
    },
    traits={"ip_address": TEST_IP, "prefix_len": 21},
)
USER_AGENT_linux_chrome = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
USER_AGENT_linux_firefox = (
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0"
)
USER_AGENT_android_chrome = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36"


class MemoryGeoipResolver:
    def __init__(self):
        self.country_db = {TEST_IP: TEST_IP_GEOIP_COUNTRY}
        self.city_db = {TEST_IP: TEST_IP_GEOIP_CITY}

    def country(self, ip):
        record = self.country_db.get(ip)
        if not record:
            raise geoip2.errors.AddressNotFoundError(ip)
        return record

    def city(self, ip):
        record = self.city_db.get(ip)
        if not record:
            raise geoip2.errors.AddressNotFoundError(ip)
        return record


MemorySessionStore = _MemorySessionStore


class HtmlTokenizer(HTMLParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tokens = []

    @classmethod
    def _attrs_to_str(cls, attrs):
        out = []
        for key, value in attrs:
            out.append(f"{key}={value!r}" if value else key)
        return " ".join(out)

    def handle_starttag(self, tag, attrs):
        self.tokens.append(f"<{tag} {self._attrs_to_str(attrs)}>")

    def handle_endtag(self, tag):
        self.tokens.append(f"</{tag}>")

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        data = data.strip()
        if data:
            self.tokens.append(data)

    @classmethod
    def tokenize(cls, source_str):
        tokenizer = cls()
        tokenizer.feed(source_str)
        return tokenizer.tokens

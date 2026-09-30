# Part of Odoo. See LICENSE file for full copyright and licensing details.

import geoip2.errors
import geoip2.models
from html.parser import HTMLParser
from odoo.http import FilesystemSessionStore
from odoo.tools._vendor.sessions import SessionStore


TEST_IP = '192.0.2.42'  # 192.0.2.0/24 are reserved for documentation,
                        # they are like example.com for ip addresses
TEST_IP_GEOIP_CITY = geoip2.models.City(
    {'continent': {'code': 'EU', 'geoname_id': 6255148, 'names': {'de': 'Europa', 'en': 'Europe', 'es': 'Europa', 'fr': 'Europe', 'ja': 'ヨーロッパ', 'pt-BR': 'Europa', 'ru': 'Европа', 'zh-CN': '欧洲'}},
     'country': {'geoname_id': 3017382, 'is_in_european_union': True, 'iso_code': 'FR', 'names': {'de': 'Frankreich', 'en': 'France', 'es': 'Francia', 'fr': 'France', 'ja': 'フランス共和国', 'pt-BR': 'França', 'ru': 'Франция', 'zh-CN': '法国'}},
     'location': {'accuracy_radius': 500, 'latitude': 48.8582, 'longitude': 2.3387, 'time_zone': 'Europe/Paris'},
     'registered_country': {'geoname_id': 3017382, 'is_in_european_union': True, 'iso_code': 'FR', 'names': {'de': 'Frankreich', 'en': 'France', 'es': 'Francia', 'fr': 'France', 'ja': 'フランス共和国', 'pt-BR': 'França', 'ru': 'Франция', 'zh-CN': '法国'}},
     'traits': {'ip_address': TEST_IP, 'prefix_len': 21},
    }, ['en']
)
TEST_IP_GEOIP_COUNTRY = geoip2.models.Country(
    {'continent': {'code': 'EU', 'geoname_id': 6255148, 'names': {'de': 'Europa', 'en': 'Europe', 'es': 'Europa', 'fr': 'Europe', 'ja': 'ヨーロッパ', 'pt-BR': 'Europa', 'ru': 'Европа', 'zh-CN': '欧洲'}},
     'country': {'geoname_id': 3017382, 'is_in_european_union': True, 'iso_code': 'FR', 'names': {'de': 'Frankreich', 'en': 'France', 'es': 'Francia', 'fr': 'France', 'ja': 'フランス共和国', 'pt-BR': 'França', 'ru': 'Франция', 'zh-CN': '法国'}},
     'registered_country': {'geoname_id': 3017382, 'is_in_european_union': True, 'iso_code': 'FR', 'names': {'de': 'Frankreich', 'en': 'France', 'es': 'Francia', 'fr': 'France', 'ja': 'フランス共和国', 'pt-BR': 'França', 'ru': 'Франция', 'zh-CN': '法国'}},
     'traits': {'ip_address': TEST_IP, 'prefix_len': 21},
    }, ['en']
)
USER_AGENT_linux_chrome = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
USER_AGENT_linux_firefox = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:126.0) Gecko/20100101 Firefox/126.0'
USER_AGENT_android_chrome = 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36'


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

class MemorySessionStore(SessionStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = {}

    def get(self, sid):
        session = self.store.get(sid)
        if not session:
            session = self.new()
        return session

    def save(self, session):
        self.store[session.sid] = session

    def delete(self, session):
        self.store.pop(session.sid, None)

    def delete_from_identifiers(self, identifiers):
        sid_to_remove = []
        for sid in self.store:
            if any(sid.startswith(identifier) for identifier in identifiers):
                sid_to_remove.append(sid)
        for sid in sid_to_remove:
            self.store.pop(sid)

    def get_missing_session_identifiers(self, identifiers):
        return set(identifiers).difference(self.store)

    def delete_old_sessions(self, session):
        return FilesystemSessionStore.delete_old_sessions(self, session)

    def rotate(self, session, env, soft=None):
        FilesystemSessionStore.rotate(self, session, env, soft)

    def generate_key(self, salt=None):
        return FilesystemSessionStore.generate_key(self, salt)

    def is_valid_key(self, key):
        return FilesystemSessionStore.is_valid_key(self, key)

    def vacuum(self):
        return


# pylint: disable=W0223(abstract-method)
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
        # HTML5 <img> instead of XHTML <img/>
        self.handle_starttag(tag, attrs)

    def handle_data(self, data):
        data = data.strip()
        if data:
            self.tokens.append(data)

    @classmethod
    def tokenize(cls, source_str):
        """
        Parse the source html into a list of tokens. Only tags and
        tags data are conserved, other elements such as comments are
        discarded.
        """
        tokenizer = cls()
        tokenizer.feed(source_str)
        return tokenizer.tokens

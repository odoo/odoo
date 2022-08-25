# Part of Odoo. See LICENSE file for full copyright and licensing details.

from html.parser import HTMLParser
from odoo.http import FilesystemSessionStore
from odoo.tools._vendor.sessions import SessionStore


class MemoryGeoipResolver:
    def resolve(self, ip):
        return {}


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

    def rotate(self, session, env):
        FilesystemSessionStore.rotate(self, session, env)

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

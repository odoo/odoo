import lxml.html.clean
import re

from importlib.metadata import version
from lxml.etree import LIBXML_VERSION

from odoo.tools import parse_version


def patch_lxml():
    # between these versions having a couple data urls in a style attribute
    # or style node removes the attribute or node erroneously
    if parse_version("4.6.0") <= parse_version(version('lxml')) < parse_version("5.2.0"):
        lxml.html.clean._find_image_dataurls = re.compile(r'data:image/(.+?);base64,').findall

    # libxml2 >= 2.14.0 stopped implicitly wrapping plain text in <p> tags.
    # We patch lxml.html parsers here to maintain compatibility across versions.
    if LIBXML_VERSION >= (2, 14, 0):
        RE_STARTS_WITH_TAG = r'^\s*<[\w!-]'
        RE_STARTS_WITH_TAG_STR = re.compile(RE_STARTS_WITH_TAG)
        RE_STARTS_WITH_TAG_BYTES = re.compile(RE_STARTS_WITH_TAG.encode('ascii'))

        orig_fromstring = lxml.html.fromstring
        orig_document_fromstring = lxml.html.document_fromstring

        def _wrap_text_node(html):
            if isinstance(html, bytes):
                if not RE_STARTS_WITH_TAG_BYTES.match(html):
                    return b"<p>%s</p>" % html.lstrip()
            else:
                if not RE_STARTS_WITH_TAG_STR.match(html):
                    return "<p>%s</p>" % html.lstrip()
            return html

        def fromstring(html, *args, **kwargs):
            return orig_fromstring(_wrap_text_node(html), *args, **kwargs)

        def document_fromstring(html, *args, **kwargs):
            return orig_document_fromstring(_wrap_text_node(html), *args, **kwargs)

        lxml.html.fromstring = fromstring
        lxml.html.document_fromstring = document_fromstring

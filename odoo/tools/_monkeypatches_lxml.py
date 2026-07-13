# Part of Odoo. See LICENSE file for full copyright and licensing details.
import lxml.html
import re

from lxml.etree import LIBXML_VERSION


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

"""
    zeep.wsdl.utils
    ~~~~~~~~~~~~~~~

"""
from urllib.parse import urlparse, urlunparse

from lxml import etree

from zeep.utils import detect_soap_env


def get_or_create_header(envelope):
    soap_env = detect_soap_env(envelope)

    # look for the Header element and create it if not found
    header_qname = "{%s}Header" % soap_env
    header = envelope.find(header_qname)
    if header is None:
        header = etree.Element(header_qname)
        envelope.insert(0, header)
    return header


def etree_to_string(node):
    return etree.tostring(
        node, pretty_print=False, xml_declaration=True, encoding="utf-8"
    )


def url_http_to_https(value):
    parts = urlparse(value)
    if parts.scheme != "http":
        return value

    # Check if the url contains ':80' and remove it if that is the case
    netloc_parts = parts.netloc.rsplit(":", 1)
    if len(netloc_parts) == 2 and netloc_parts[1] == "80":
        netloc = netloc_parts[0]
    else:
        netloc = parts.netloc
    return urlunparse(("https", netloc) + parts[2:])

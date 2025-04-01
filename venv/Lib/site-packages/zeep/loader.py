import os.path
import typing
from urllib.parse import urljoin, urlparse, urlunparse

from defusedxml.lxml import fromstring
from lxml import etree

from zeep.exceptions import XMLSyntaxError
from zeep.settings import Settings


class ImportResolver(etree.Resolver):
    """Custom lxml resolve to use the transport object"""

    def __init__(self, transport):
        self.transport = transport

    def resolve(self, url, pubid, context):
        if urlparse(url).scheme in ("http", "https"):
            content = self.transport.load(url)
            return self.resolve_string(content, context)


def parse_xml(content: str, transport, base_url=None, settings=None):
    """Parse an XML string and return the root Element.

    :param content: The XML string
    :type content: str
    :param transport: The transport instance to load imported documents
    :type transport: zeep.transports.Transport
    :param base_url: The base url of the document, used to make relative
      lookups absolute.
    :type base_url: str
    :param settings: A zeep.settings.Settings object containing parse settings.
    :type settings: zeep.settings.Settings
    :returns: The document root
    :rtype: lxml.etree._Element

    """
    settings = settings or Settings()
    recover = not settings.strict
    parser = etree.XMLParser(
        remove_comments=True,
        resolve_entities=False,
        recover=recover,
        huge_tree=settings.xml_huge_tree,
    )
    parser.resolvers.add(ImportResolver(transport))
    try:
        return fromstring(
            content,
            parser=parser,
            base_url=base_url,
            forbid_dtd=settings.forbid_dtd,
            forbid_entities=settings.forbid_entities,
        )
    except etree.XMLSyntaxError as exc:
        raise XMLSyntaxError(
            "Invalid XML content received (%s)" % exc.msg, content=content
        )


def load_external(url: typing.IO, transport, base_url=None, settings=None):
    """Load an external XML document.

    :param url:
    :param transport:
    :param base_url:
    :param settings: A zeep.settings.Settings object containing parse settings.
    :type settings: zeep.settings.Settings

    """
    settings = settings or Settings()
    if hasattr(url, "read"):
        content = url.read()
    else:
        if base_url:
            url = absolute_location(url, base_url)
        content = transport.load(url)
    return parse_xml(content, transport, base_url, settings=settings)


async def load_external_async(url: typing.IO, transport, base_url=None, settings=None):
    """Load an external XML document.

    :param url:
    :param transport:
    :param base_url:
    :param settings: A zeep.settings.Settings object containing parse settings.
    :type settings: zeep.settings.Settings

    """
    settings = settings or Settings()
    if hasattr(url, "read"):
        content = url.read()
    else:
        if base_url:
            url = absolute_location(url, base_url)
        content = await transport.load(url)
    return parse_xml(content, transport, base_url, settings=settings)


def normalize_location(settings, url, base_url):
    """Return a 'normalized' url for the given url.

    This will make the url absolute and force it to https when that setting is
    enabled.

    """
    if base_url:
        url = absolute_location(url, base_url)

    if base_url and settings.force_https:
        base_url_parts = urlparse(base_url)
        url_parts = urlparse(url)
        if (
            base_url_parts.netloc == url_parts.netloc
            and base_url_parts.scheme != url_parts.scheme
        ):
            url = urlunparse(("https",) + url_parts[1:])
    return url


def absolute_location(location, base):
    """Make an url absolute (if it is optional) via the passed base url.

    :param location: The (relative) url
    :type location: str
    :param base: The base location
    :type base: str
    :returns: An absolute URL
    :rtype: str

    """
    if location == base:
        return location

    if urlparse(location).scheme in ("http", "https", "file"):
        return location

    if base and urlparse(base).scheme in ("http", "https", "file"):
        return urljoin(base, location)
    else:
        if os.path.isabs(location):
            return location
        if base:
            return os.path.realpath(os.path.join(os.path.dirname(base), location))
    return location


def is_relative_path(value):
    """Check if the given value is a relative path

    :param value: The value
    :type value: str
    :returns: Boolean indicating if the url is relative. If it is absolute then
      False is returned.
    :rtype: boolean

    """
    if urlparse(value).scheme in ("http", "https", "file"):
        return False
    return not os.path.isabs(value)

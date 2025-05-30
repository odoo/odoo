import datetime
from uuid import uuid4

import pytz
from lxml import etree
from lxml.builder import ElementMaker

from zeep import ns
from zeep.wsdl.utils import get_or_create_header

NSMAP = {"wsse": ns.WSSE, "wsu": ns.WSU}
WSSE = ElementMaker(namespace=NSMAP["wsse"], nsmap={"wsse": ns.WSSE})
WSU = ElementMaker(namespace=NSMAP["wsu"], nsmap={"wsu": ns.WSU})
ID_ATTR = etree.QName(NSMAP["wsu"], "Id")


def get_security_header(doc):
    """Return the security header. If the header doesn't exist it will be
    created.

    """
    header = get_or_create_header(doc)
    security = header.find("wsse:Security", namespaces=NSMAP)
    if security is None:
        security = WSSE.Security()
        header.append(security)
    return security


def get_timestamp(timestamp=None, zulu_timestamp=None):
    timestamp = timestamp or datetime.datetime.utcnow()
    timestamp = timestamp.replace(tzinfo=pytz.utc, microsecond=0)
    if zulu_timestamp:
        return timestamp.isoformat().replace("+00:00", "Z")
    else:
        return timestamp.isoformat()


def get_unique_id():
    return "id-{0}".format(uuid4())


def ensure_id(node):
    """Ensure given node has a wsu:Id attribute; add unique one if not.

    Return found/created attribute value.

    """
    assert node is not None
    id_val = node.get(ID_ATTR)
    if not id_val:
        id_val = get_unique_id()
        node.set(ID_ATTR, id_val)
    return id_val

from lxml import etree

from zeep import ns


def xsi_ns(localname: str) -> etree.QName:
    return etree.QName(ns.XSI, localname)


def xsd_ns(localname: str) -> etree.QName:
    return etree.QName(ns.XSD, localname)


class _StaticIdentity:
    def __init__(self, val):
        self.__value__ = val

    def __repr__(self):
        return self.__value__


NotSet = _StaticIdentity("NotSet")
SkipValue = _StaticIdentity("SkipValue")
Nil = _StaticIdentity("Nil")


AUTO_IMPORT_NAMESPACES = ["http://schemas.xmlsoap.org/soap/encoding/"]

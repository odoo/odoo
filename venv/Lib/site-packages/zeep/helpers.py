import datetime
from collections import OrderedDict

from lxml import etree

from zeep import xsd
from zeep.xsd.valueobjects import CompoundValue


def serialize_object(obj, target_cls=OrderedDict):
    """Serialize zeep objects to native python data structures"""
    if isinstance(obj, list):
        return [serialize_object(sub, target_cls) for sub in obj]

    if isinstance(obj, (dict, CompoundValue)):
        result = target_cls()
        for key in obj:
            result[key] = serialize_object(obj[key], target_cls)
        return result

    return obj


def create_xml_soap_map(values):
    """Create an http://xml.apache.org/xml-soap#Map value."""
    Map = xsd.ComplexType(
        xsd.Sequence(
            [xsd.Element("item", xsd.AnyType(), min_occurs=1, max_occurs="unbounded")]
        ),
        qname=etree.QName("{http://xml.apache.org/xml-soap}Map"),
    )

    KeyValueData = xsd.Element(
        "{http://xml.apache.org/xml-soap}KeyValueData",
        xsd.ComplexType(
            xsd.Sequence(
                [xsd.Element("key", xsd.AnyType()), xsd.Element("value", xsd.AnyType())]
            )
        ),
    )

    return Map(
        item=[
            KeyValueData(
                xsd.AnyObject(xsd.String(), key),
                xsd.AnyObject(guess_xsd_type(value), value),
            )
            for key, value in values.items()
        ]
    )


def guess_xsd_type(obj):
    """Return the XSD Type for the given object"""
    if isinstance(obj, bool):
        return xsd.Boolean()
    if isinstance(obj, int):
        return xsd.Integer()
    if isinstance(obj, float):
        return xsd.Float()
    if isinstance(obj, datetime.datetime):
        return xsd.DateTime()
    if isinstance(obj, datetime.date):
        return xsd.Date()
    return xsd.String()


def Nil():
    """Return an xsi:nil element"""
    return xsd.AnyObject(None, None)

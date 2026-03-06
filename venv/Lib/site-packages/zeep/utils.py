import cgi
import inspect
import typing

from lxml import etree

from zeep.exceptions import XMLParseError
from zeep.ns import XSD


def qname_attr(
    node: etree._Element,
    attr_name: typing.Union[str, etree.QName],
    target_namespace=None,
) -> typing.Optional[etree.QName]:
    value = node.get(attr_name)
    if value is not None:
        return as_qname(value, node.nsmap, target_namespace)
    return None


def as_qname(value: str, nsmap, target_namespace=None) -> etree.QName:
    """Convert the given value to a QName"""
    value = value.strip()  # some xsd's contain leading/trailing spaces
    if ":" in value:
        prefix, local = value.split(":")

        # The xml: prefix is always bound to the XML namespace, see
        # https://www.w3.org/TR/xml-names/
        if prefix == "xml":
            namespace = "http://www.w3.org/XML/1998/namespace"
        else:
            namespace = nsmap.get(prefix)

        if not namespace:
            raise XMLParseError("No namespace defined for %r (%r)" % (prefix, value))

        # Workaround for https://github.com/mvantellingen/python-zeep/issues/349
        if not local:
            return etree.QName(XSD, "anyType")

        return etree.QName(namespace, local)

    if target_namespace:
        return etree.QName(target_namespace, value)

    if nsmap.get(None):
        return etree.QName(nsmap[None], value)
    return etree.QName(value)


def findall_multiple_ns(node: etree._Element, name, namespace_sets):
    result = []
    for nsmap in namespace_sets:
        result.extend(node.findall(name, namespaces=nsmap))
    return result


def get_version():
    from zeep import __version__  # cyclic import

    return __version__


def get_base_class(objects):
    """Return the best base class for multiple objects.

    Implementation is quick and dirty, might be done better.. ;-)

    """
    bases = [inspect.getmro(obj.__class__)[::-1] for obj in objects]
    num_objects = len(objects)
    max_mro = max(len(mro) for mro in bases)

    base_class = None
    for i in range(max_mro):
        try:
            if len({bases[j][i] for j in range(num_objects)}) > 1:
                break
        except IndexError:
            break
        base_class = bases[0][i]
    return base_class


def detect_soap_env(envelope):
    root_tag = etree.QName(envelope)
    return root_tag.namespace


def get_media_type(value):
    """Parse a HTTP content-type header and return the media-type"""
    main_value, parameters = cgi.parse_header(value)
    return main_value.lower()

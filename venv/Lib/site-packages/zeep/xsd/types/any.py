import logging
import typing

from cached_property import threaded_cached_property
from lxml import etree

from zeep.utils import qname_attr
from zeep.xsd.const import xsd_ns, xsi_ns
from zeep.xsd.context import XmlParserContext
from zeep.xsd.types.base import Type
from zeep.xsd.valueobjects import AnyObject, CompoundValue

if typing.TYPE_CHECKING:
    from zeep.xsd.schema import Schema
    from zeep.xsd.types.complex import ComplexType

logger = logging.getLogger(__name__)

__all__ = ["AnyType"]


class AnyType(Type):
    _default_qname = xsd_ns("anyType")
    _element = None

    def __call__(self, value=None):
        return value or ""

    def render(
        self,
        node: etree._Element,
        value: typing.Union[list, dict, CompoundValue],
        xsd_type: "ComplexType" = None,
        render_path=None,
    ) -> None:
        assert xsd_type is None

        if isinstance(value, AnyObject):
            if value.xsd_type is None:
                node.set(xsi_ns("nil"), "true")
            else:
                value.xsd_type.render(node, value.value, None, render_path)
                node.set(xsi_ns("type"), value.xsd_type.qname)
        elif isinstance(value, CompoundValue):
            value._xsd_elm.render(node, value, render_path)
            node.set(xsi_ns("type"), value._xsd_elm.qname)
        else:
            node.text = self.xmlvalue(value)

    def parse_xmlelement(
        self,
        xmlelement: etree._Element,
        schema: "Schema" = None,
        allow_none: bool = True,
        context: XmlParserContext = None,
        schema_type: "Type" = None,
    ) -> typing.Optional[typing.Union[str, CompoundValue, typing.List[etree._Element]]]:
        """Try to parse the xml element and return a value for it.

        There is a big chance that we cannot parse this value since it is an
        Any. In that case we just return the raw lxml Element nodes.

        :param xmlelement: XML element objects
        :param schema: The parent XML schema
        :param allow_none: Allow none
        :param context: Optional parsing context (for inline schemas)
        :param schema_type: The original type (not overriden via xsi:type)

        """
        xsi_type = qname_attr(xmlelement, xsi_ns("type"))
        xsi_nil = xmlelement.get(xsi_ns("nil"))
        children = list(xmlelement)

        # Handle xsi:nil attribute
        if xsi_nil == "true":
            return None

        # Check if a xsi:type is defined and try to parse the xml according
        # to that type.
        if xsi_type and schema:
            xsd_type = schema.get_type(xsi_type, fail_silently=True)

            # If we were unable to resolve a type for the xsi:type (due to
            # buggy soap servers) then we just return the text or lxml element.
            if not xsd_type:
                logger.debug(
                    "Unable to resolve type for %r, returning raw data", xsi_type.text
                )

                if xmlelement.text:
                    return self.pythonvalue(xmlelement.text)
                return children

            # If the xsd_type is xsd:anyType then we will recurs so ignore
            # that.
            if isinstance(xsd_type, self.__class__):
                return self.pythonvalue(xmlelement.text) or None

            return xsd_type.parse_xmlelement(xmlelement, schema, context=context)

        # If no xsi:type is set and the element has children then there is
        # not much we can do. Just return the children
        elif children:
            return children

        elif xmlelement.text is not None:
            return self.pythonvalue(xmlelement.text)

        return None

    def resolve(self):
        return self

    def xmlvalue(self, value):
        """Guess the xsd:type for the value and use corresponding serializer"""
        from zeep.xsd.types import builtins

        available_types = [
            builtins.String,
            builtins.Boolean,
            builtins.Decimal,
            builtins.Float,
            builtins.DateTime,
            builtins.Date,
            builtins.Time,
        ]
        for xsd_type in available_types:
            if isinstance(value, tuple(xsd_type.accepted_types)):
                return xsd_type().xmlvalue(value)
        return str(value)

    def pythonvalue(self, value, schema=None) -> typing.Optional[str]:
        return value if value is not None else None

    def signature(self, schema=None, standalone=True):
        return "xsd:anyType"

    @threaded_cached_property
    def _attributes_unwrapped(self):
        return []

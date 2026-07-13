import typing

from lxml import etree

from zeep.xsd.context import XmlParserContext
from zeep.xsd.utils import create_prefixed_name
from zeep.xsd.valueobjects import CompoundValue

if typing.TYPE_CHECKING:
    from zeep.xsd.schema import Schema
    from zeep.xsd.types.complex import ComplexType

__all__ = ["Type"]


class Type:
    def __init__(self, qname=None, is_global=False):
        self.qname = qname
        self.name = qname.localname if qname else None
        self._resolved = False
        self.is_global = is_global

    def get_prefixed_name(self, schema):
        return create_prefixed_name(self.qname, schema)

    def accept(self, value):
        raise NotImplementedError

    @property
    def accepted_types(self) -> typing.List[typing.Type]:
        return []

    def validate(self, value, required=False):
        return

    def parse_kwargs(self, kwargs, name, available_kwargs):
        value = None
        name = name or self.name

        if name in available_kwargs:
            value = kwargs[name]
            available_kwargs.remove(name)
            return {name: value}
        return {}

    def parse_xmlelement(
        self,
        xmlelement: etree._Element,
        schema: "Schema" = None,
        allow_none: bool = True,
        context: XmlParserContext = None,
        schema_type: "Type" = None,
    ) -> typing.Optional[typing.Union[str, CompoundValue, typing.List[etree._Element]]]:
        raise NotImplementedError(
            "%s.parse_xmlelement() is not implemented" % self.__class__.__name__
        )

    def parsexml(self, xml, schema=None):
        raise NotImplementedError

    def render(
        self,
        node: etree._Element,
        value: typing.Union[list, dict, CompoundValue],
        xsd_type: "ComplexType" = None,
        render_path=None,
    ) -> None:
        raise NotImplementedError(
            "%s.render() is not implemented" % self.__class__.__name__
        )

    def resolve(self):
        raise NotImplementedError(
            "%s.resolve() is not implemented" % self.__class__.__name__
        )

    def extend(self, child):
        raise NotImplementedError(
            "%s.extend() is not implemented" % self.__class__.__name__
        )

    def restrict(self, child):
        raise NotImplementedError(
            "%s.restrict() is not implemented" % self.__class__.__name__
        )

    @property
    def attributes(self):
        return []

    @classmethod
    def signature(cls, schema=None, standalone=True):
        return ""

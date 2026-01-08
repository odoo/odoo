import typing

from lxml import etree

from zeep.utils import get_base_class
from zeep.xsd.context import XmlParserContext
from zeep.xsd.types.simple import AnySimpleType

if typing.TYPE_CHECKING:
    from zeep.xsd.schema import Schema
    from zeep.xsd.types.base import Type
    from zeep.xsd.types.complex import ComplexType
    from zeep.xsd.valueobjects import CompoundValue

__all__ = ["ListType", "UnionType"]


class ListType(AnySimpleType):
    """Space separated list of simpleType values"""

    def __init__(self, item_type):
        self.item_type = item_type
        super().__init__()

    def __call__(self, value):
        return value

    def render(
        self,
        node: etree._Element,
        value: typing.Union[list, dict, "CompoundValue"],
        xsd_type: "ComplexType" = None,
        render_path=None,
    ) -> None:
        assert xsd_type is None
        node.text = self.xmlvalue(value)

    def resolve(self):
        self.item_type = self.item_type.resolve()
        self.base_class = self.item_type.__class__
        return self

    def xmlvalue(self, value):
        item_type = self.item_type
        return " ".join(item_type.xmlvalue(v) for v in value)

    def pythonvalue(self, value):
        if not value:
            return []
        item_type = self.item_type
        return [item_type.pythonvalue(v) for v in value.split()]

    def signature(self, schema=None, standalone=True):
        return self.item_type.signature(schema) + "[]"


class UnionType(AnySimpleType):
    """Simple type existing out of multiple other types"""

    def __init__(self, item_types):
        self.item_types = item_types
        self.item_class = None
        assert item_types
        super().__init__(None)

    def resolve(self):
        self.item_types = [item.resolve() for item in self.item_types]
        base_class = get_base_class(self.item_types)
        if issubclass(base_class, AnySimpleType) and base_class != AnySimpleType:
            self.item_class = base_class
        return self

    def signature(self, schema=None, standalone=True):
        return ""

    def parse_xmlelement(
        self,
        xmlelement: etree._Element,
        schema: "Schema" = None,
        allow_none: bool = True,
        context: XmlParserContext = None,
        schema_type: "Type" = None,
    ) -> typing.Optional[
        typing.Union[str, "CompoundValue", typing.List[etree._Element]]
    ]:
        if self.item_class:
            return self.item_class().parse_xmlelement(
                xmlelement, schema, allow_none, context
            )
        return str(xmlelement.text) or None

    def pythonvalue(self, value):
        if self.item_class:
            return self.item_class().pythonvalue(value)
        return value

    def xmlvalue(self, value):
        if self.item_class:
            return self.item_class().xmlvalue(value)
        return value

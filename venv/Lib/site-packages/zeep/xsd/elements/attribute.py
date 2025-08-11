import logging

from lxml import etree

from zeep import exceptions
from zeep.xsd.const import NotSet
from zeep.xsd.elements.element import Element

logger = logging.getLogger(__name__)

__all__ = ["Attribute", "AttributeGroup"]


class Attribute(Element):
    def __init__(self, name, type_=None, required=False, default=None):
        super().__init__(name=name, type_=type_, default=default)
        self.required = required
        self.array_type = None

    def parse(self, value):
        try:
            return self.type.pythonvalue(value)
        except (TypeError, ValueError):
            logger.exception("Error during xml -> python translation")
            return None

    def render(self, parent, value, render_path=None):
        if value in (None, NotSet) and not self.required:
            return

        self.validate(value, render_path)

        value = self.type.xmlvalue(value)
        parent.set(self.qname, value)

    def validate(self, value, render_path):
        try:
            self.type.validate(value, required=self.required)
        except exceptions.ValidationError as exc:
            raise exceptions.ValidationError(
                "The attribute %s is not valid: %s" % (self.qname, exc.message),
                path=render_path,
            )

    def clone(self, *args, **kwargs):
        array_type = kwargs.pop("array_type", None)
        new = super().clone(*args, **kwargs)
        new.array_type = array_type
        return new

    def resolve(self):
        retval = super().resolve()
        self.type = self.type.resolve()
        if self.array_type:
            retval.array_type = self.array_type.resolve()
        return retval


class AttributeGroup:
    def __init__(self, name, attributes):
        if not isinstance(name, etree.QName):
            name = etree.QName(name)

        self.name = name.localname
        self.qname = name
        self.type = None
        self._attributes = attributes
        self.is_global = True

    @property
    def attributes(self):
        result = []
        for attr in self._attributes:
            if isinstance(attr, AttributeGroup):
                result.extend(attr.attributes)
            else:
                result.append(attr)
        return result

    def resolve(self):
        resolved = []
        for attribute in self._attributes:
            value = attribute.resolve()
            assert value is not None
            if isinstance(value, list):
                resolved.extend(value)
            else:
                resolved.append(value)
        self._attributes = resolved
        return self

    def signature(self, schema=None, standalone=True):
        return ", ".join(attr.signature(schema) for attr in self._attributes)

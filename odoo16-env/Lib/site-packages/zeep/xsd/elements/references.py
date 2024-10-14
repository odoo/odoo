"""
zeep.xsd.elements.references
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ref* objecs are only used temporarily between parsing the schema and resolving
all the elements.

"""

__all__ = ["RefElement", "RefAttribute", "RefAttributeGroup", "RefGroup"]


class RefElement:
    def __init__(
        self, tag, ref, schema, is_qualified=False, min_occurs=1, max_occurs=1
    ):
        self._ref = ref
        self._is_qualified = is_qualified
        self._schema = schema
        self.min_occurs = min_occurs
        self.max_occurs = max_occurs

    def resolve(self):
        elm = self._schema.get_element(self._ref)
        elm = elm.clone(
            elm.qname, min_occurs=self.min_occurs, max_occurs=self.max_occurs
        )
        return elm.resolve()


class RefAttribute(RefElement):
    def __init__(self, *args, **kwargs):
        self._array_type = kwargs.pop("array_type", None)
        super().__init__(*args, **kwargs)

    def resolve(self):
        attrib = self._schema.get_attribute(self._ref)
        attrib = attrib.clone(attrib.qname, array_type=self._array_type)
        return attrib.resolve()


class RefAttributeGroup(RefElement):
    def resolve(self):
        value = self._schema.get_attribute_group(self._ref)
        return value.resolve()


class RefGroup(RefElement):
    def resolve(self):
        elm = self._schema.get_group(self._ref)
        elm = elm.clone(
            elm.qname, min_occurs=self.min_occurs, max_occurs=self.max_occurs
        )
        return elm

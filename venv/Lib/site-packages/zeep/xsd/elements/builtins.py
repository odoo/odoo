from __future__ import division

from zeep.xsd.const import xsd_ns
from zeep.xsd.elements.base import Base


class Schema(Base):
    name = "schema"
    attr_name = "schema"
    qname = xsd_ns("schema")

    def clone(self, qname, min_occurs=1, max_occurs=1):
        return self.__class__()

    def parse_kwargs(self, kwargs, name, available_kwargs):
        if name in available_kwargs:
            value = kwargs[name]
            available_kwargs.remove(name)
            return {name: value}
        return {}

    def parse(self, xmlelement, schema, context=None):
        from zeep.xsd.schema import Schema as _Schema

        schema = _Schema(xmlelement, schema._transport)
        context.schemas.append(schema)
        return schema

    def parse_xmlelements(self, xmlelements, schema, name=None, context=None):
        if xmlelements[0].tag == self.qname:
            xmlelement = xmlelements.popleft()
            result = self.parse(xmlelement, schema, context=context)
            return result

    def resolve(self):
        return self


_elements = [Schema]

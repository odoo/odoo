# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64
import collections.abc
import datetime
import functools
import json
import xmlrpc.client

from lxml import etree
from lxml.builder import E  # pylint: disable=no-name-in-module

from odoo import models, http


class XMLRPCMarshaller:
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding
        self.memo = set()

    def dumps(self, values):
        if isinstance(values, xmlrpc.client.Fault):
            tree = E.fault(self.serialize({
                'faultCode': values.faultCode,
                'faultString': values.faultString,
            }))
        else:
            tree = E.params()
            tree.extend(E.param(self.serialize(value)) for value in values)
        return etree.tostring(tree, encoding=self.encoding, xml_declaration=False)

    @functools.singledispatchmethod
    def serialize(self, value):
        # Default serializer if no specilized one matched
        return self.serialize(vars(value))

    @serialize.register
    def dump_model(self, value: models.BaseModel):
        return self.serialize(value.ids)

    @serialize.register
    def dump_none(self, value: type(None)):
        return E.value(E.nil())

    @serialize.register
    def dump_bool(self, value: bool):
        return E.value(E.boolean("1" if value else "0"))

    @serialize.register
    def dump_int(self, value: int):
        if not (xmlrpc.client.MININT <= value <= xmlrpc.client.MAXINT):
            raise OverflowError("int exceeds XML-RPC limits")
        return E.value(E.int(str(value)))

    @serialize.register
    def dump_float(self, value: float):
        return E.value(E.double(repr(value)))

    @serialize.register
    def dump_str(self, value: str):
        return E.value(E.string(value))

    @serialize.register
    def dump_mapping(self, value: collections.abc.Mapping):
        m = id(value)
        if m in self.memo:
            raise TypeError("cannot marshal recursive dictionaries")
        self.memo.add(m)
        struct = E.struct()
        struct.extend(
            # coerce all keys to string (same as JSON)
            E.member(E.name(str(k)), self.serialize(v))
            for k, v in value.items()
        )
        self.memo.remove(m)
        return E.value(struct)

    @serialize.register
    def dump_iterable(self, value: collections.abc.Iterable):
        m = id(value)
        if m in self.memo:
            raise TypeError("cannot marshal recursive sequences")
        self.memo.add(m)
        data = E.data()
        data.extend(self.serialize(v) for v in value)
        self.memo.remove(m)
        return E.value(E.array(data))

    @serialize.register
    def dump_datetime(self, value: datetime.datetime):
        d = etree.Element('dateTime.iso8601')
        d.text = value.replace(microsecond=0).isoformat()
        return E.value(d)

    @serialize.register
    def dump_date(self, value: datetime.date):
        d = etree.Element('dateTime.iso8601')
        d.text = value.isoformat()
        return E.value(d)

    @serialize.register
    def dump_bytes(self, value: bytes):
        return E.value(E.base64(base64.b64encode(value).decode()))


class JSONMarshaller(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime.datetime):
            return o.replace(microsecond=0).isoformat()
        if isinstance(o, models.BaseModel):
            return o.ids
        if isinstance(o, collections.abc.Mapping):
            return dict(o)
        if isinstance(o, collections.abc.Iterable):
            return list(o)
        if isinstance(o, Exception):
            return http.serialize_exception(o)
        return super().default(o)

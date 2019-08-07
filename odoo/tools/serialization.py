# -*- coding: utf-8 -*-
import json
import xmlrpc.client

from datetime import date, datetime

import odoo

from .func import lazy
from . import ustr


class OdooMarshaller(xmlrpc.client.Marshaller):

    """
    XMLRPC marshaller capable of converting different python objects used by Odoo
    """

    dispatch = dict(xmlrpc.client.Marshaller.dispatch)

    def _Marshaller__dump(self, value, write):
        # we cannot create a hook for recordsets like for datetime and date objects, because
        # a recordset of say 'res.users' is not of the same type as a recordset of 'sale.order'
        # and the __dump function checks for type() and not for isinstance() to determine if an
        # object is marshallable.
        # to circumvent this, we check if the object is an instance of BaseModel, which applies
        # to all recordsets, and then we convert it to id
        if type(value) not in OdooMarshaller.dispatch and isinstance(value, odoo.models.BaseModel):
            value = value.ids
        super()._Marshaller__dump(value, write)

    def dump_datetime(self, value, write):
        # override to marshall as a string for backwards compatibility
        value = odoo.fields.Datetime.to_string(value)
        self.dump_unicode(value, write)
    dispatch[datetime] = dump_datetime

    def dump_date(self, value, write):
        value = odoo.fields.Date.to_string(value)
        self.dump_unicode(value, write)
    dispatch[date] = dump_date


# monkey-patch xmlrpc.client's marshaller
xmlrpc.client.Marshaller = OdooMarshaller


class OdooEncoder(json.JSONEncoder):

    """
    JSON Encoder capable of converting different python objects used by Odoo
    """

    def _serialize_datetime(self, o):
        return odoo.fields.Datetime.to_string(o)

    def _serialize_date(self, o):
        return odoo.fields.Date.to_string(o)

    def _serialize_recordset(self, o):
        return o.ids

    def _serialize_lazy(self, o):
        return o._value

    def _serialize_bytes(self, o):
        return ustr(o)

    def default(self, o):
        if isinstance(o, lazy):
            return self._serialize_lazy(o)
        if isinstance(o, datetime):
            return self._serialize_datetime(o)
        if isinstance(o, date):
            # order of if-statement is important, datetime objects are instances of date
            return self._serialize_date(o)
        if isinstance(o, odoo.models.BaseModel):
            return self._serialize_recordset(o)
        if isinstance(o, bytes):
            return self._serialize_bytes(o)
        return super().default(o)


# monkey-patch json._default_encoder and json.JSONEncoder
json.JSONEncoder = OdooEncoder
json._default_encoder = OdooEncoder(
    skipkeys=False,
    ensure_ascii=True,
    check_circular=True,
    allow_nan=True,
    indent=None,
    separators=None,
    default=None
)

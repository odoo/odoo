# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# pylint: disable=import-outside-toplevel

import re
from markupsafe import Markup
from datetime import date, datetime
from odoo.tools import lazy, ustr
from odoo.tools.misc import frozendict
from odoo.fields import Date, Datetime, Command
from odoo.tools._monkeypatches import monkeypatch_register


@monkeypatch_register('xmlrpc')
def monkeypatch_xmlrpc():
    """ XmlRPC fix: Dispatching has changed in xmlrpc.client versions
        but we want it to have consistent behaviour with our datatypes.
    """

    import xmlrpc.client

    # ustr decodes as utf-8 or latin1 so we can search for the ASCII bytes
    #   Char ::= #x9 | #xA | #xD | [#x20-#xD7FF]
    XML_INVALID = re.compile(b'[\x00-\x08\x0B\x0C\x0F-\x1F]')


    class OdooMarshaller(xmlrpc.client.Marshaller):
        dispatch = dict(xmlrpc.client.Marshaller.dispatch)

        def dump_frozen_dict(self, value, write):
            value = dict(value)
            self.dump_struct(value, write)

        # By default, in xmlrpc, bytes are converted to xmlrpc.client.Binary object.
        # Historically, odoo is sending binary as base64 string.
        # In python 3, base64.b64{de,en}code() methods now works on bytes.
        # Convert them to str to have a consistent behavior between python 2 and python 3.
        def dump_bytes(self, value, write):
            # XML 1.0 disallows control characters, check for them immediately to
            # see if this is a "real" binary (rather than base64 or somesuch) and
            # blank it out, otherwise they get embedded in the output and break
            # client-side parsers
            if XML_INVALID.search(value):
                self.dump_unicode('', write)
            else:
                self.dump_unicode(ustr(value), write)

        def dump_datetime(self, value, write):
            # override to marshall as a string for backwards compatibility
            value = Datetime.to_string(value)
            self.dump_unicode(value, write)

        # convert date objects to strings in iso8061 format.
        def dump_date(self, value, write):
            value = Date.to_string(value)
            self.dump_unicode(value, write)

        def dump_lazy(self, value, write):
            v = value._value
            return self.dispatch[type(v)](self, v, write)

        dispatch[frozendict] = dump_frozen_dict
        dispatch[bytes] = dump_bytes
        dispatch[datetime] = dump_datetime
        dispatch[date] = dump_date
        dispatch[lazy] = dump_lazy
        dispatch[Command] = dispatch[int]
        dispatch[Markup] = lambda self, value, write: self.dispatch[str](self, str(value), write)

    # monkey-patch xmlrpc.client's marshaller
    xmlrpc.client.Marshaller = OdooMarshaller

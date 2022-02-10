import re
import sys
import traceback
import xmlrpc.client
from datetime import date, datetime

from markupsafe import Markup
from werkzeug.wrappers import Response

import odoo
from odoo.http import Controller, request, route
from odoo.fields import Date, Datetime, Command
from odoo.service import dispatch_rpc
from odoo.tools import lazy, ustr
from odoo.tools.misc import frozendict

# ==========================================================
# XML-RPC helpers
# ==========================================================

# XML-RPC fault codes. Some care must be taken when changing these: the
# constants are also defined client-side and must remain in sync.
# User code must use the exceptions defined in ``odoo.exceptions`` (not
# create directly ``xmlrpc.client.Fault`` objects).
RPC_FAULT_CODE_CLIENT_ERROR = 1 # indistinguishable from app. error.
RPC_FAULT_CODE_APPLICATION_ERROR = 1
RPC_FAULT_CODE_WARNING = 2
RPC_FAULT_CODE_ACCESS_DENIED = 3
RPC_FAULT_CODE_ACCESS_ERROR = 4

# ustr decodes as utf-8 or latin1 so we can search for the ASCII bytes
#   Char ::= #x9 | #xA | #xD | [#x20-#xD7FF]
XML_INVALID = re.compile(b'[\x00-\x08\x0B\x0C\x0F-\x1F]')


def xmlrpc_handle_exception_int(e):
    if isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_WARNING, str(e))
    elif isinstance(e, odoo.exceptions.AccessError):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_ACCESS_ERROR, str(e))
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
    elif isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_WARNING, str(e))
    else:
        info = sys.exc_info()
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)

    return xmlrpc.client.dumps(fault, allow_none=None)


def xmlrpc_handle_exception_string(e):
    if isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpc.client.Fault('warning -- Warning\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.MissingError):
        fault = xmlrpc.client.Fault('warning -- MissingError\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.AccessError):
        fault = xmlrpc.client.Fault('warning -- AccessError\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpc.client.Fault('AccessDenied', str(e))
    elif isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpc.client.Fault('warning -- UserError\n\n' + str(e), '')
    #InternalError
    else:
        info = sys.exc_info()
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpc.client.Fault(odoo.tools.exception_to_unicode(e), formatted_info)

    return xmlrpc.client.dumps(fault, allow_none=None, encoding=None)


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

# ==========================================================
# RPC Controller
# ==========================================================
class RPC(Controller):
    """Handle RPC connections."""

    def _xmlrpc(self, service):
        """Common method to handle an XML-RPC request."""
        data = request.httprequest.get_data()
        params, method = xmlrpc.client.loads(data)
        result = dispatch_rpc(service, method, params)
        return xmlrpc.client.dumps((result,), methodresponse=1, allow_none=False)

    @route("/xmlrpc/<service>", auth="none", methods=["POST"], csrf=False, save_session=False)
    def xmlrpc_1(self, service):
        """XML-RPC service that returns faultCode as strings.

        This entrypoint is historical and non-compliant, but kept for
        backwards-compatibility.
        """
        try:
            response = self._xmlrpc(service)
        except Exception as error:
            response = xmlrpc_handle_exception_string(error)
        return Response(response=response, mimetype='text/xml')

    @route("/xmlrpc/2/<service>", auth="none", methods=["POST"], csrf=False, save_session=False)
    def xmlrpc_2(self, service):
        """XML-RPC service that returns faultCode as int."""
        try:
            response = self._xmlrpc(service)
        except Exception as error:
            response = xmlrpc_handle_exception_int(error)
        return Response(response=response, mimetype='text/xml')

    @route('/jsonrpc', type='json', auth="none", save_session=False)
    def jsonrpc(self, service, method, args):
        """ Method used by client APIs to contact OpenERP. """
        return dispatch_rpc(service, method, args)

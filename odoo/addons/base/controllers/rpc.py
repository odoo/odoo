from datetime import date, datetime
import xmlrpc.client

from werkzeug.wrappers import Response

from odoo.http import Controller, request, route
from odoo.fields import Date, Datetime, Command
from odoo.tools import lazy

#-----------------------------------------------------------
# XML-RPC helpers
#-----------------------------------------------------------

# XML-RPC fault codes. Some care must be taken when changing these: the
# constants are also defined client-side and must remain in sync.
# User code must use the exceptions defined in ``odoo.exceptions`` (not
# create directly ``xmlrpc.client.Fault`` objects).
RPC_FAULT_CODE_CLIENT_ERROR = 1 # indistinguishable from app. error.
RPC_FAULT_CODE_APPLICATION_ERROR = 1
RPC_FAULT_CODE_WARNING = 2
RPC_FAULT_CODE_ACCESS_DENIED = 3
RPC_FAULT_CODE_ACCESS_ERROR = 4

def xmlrpc_handle_exception_int(e):
    if isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_WARNING, odoo.tools.ustr(e.name))
    elif isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_WARNING, str(e))
    elif isinstance(e, odoo.exceptions.MissingError):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_WARNING, str(e))
    elif isinstance (e, odoo.exceptions.AccessError):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_ACCESS_ERROR, str(e))
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_ACCESS_DENIED, str(e))
    elif isinstance(e, odoo.exceptions.DeferredException):
        info = e.traceback
        # Which one is the best ?
        formatted_info = "".join(traceback.format_exception(*info))
        #formatted_info = odoo.tools.exception_to_unicode(e) + '\n' + info
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)
    else:
        info = sys.exc_info()
        # Which one is the best ?
        formatted_info = "".join(traceback.format_exception(*info))
        #formatted_info = odoo.tools.exception_to_unicode(e) + '\n' + info
        fault = xmlrpc.client.Fault(RPC_FAULT_CODE_APPLICATION_ERROR, formatted_info)

    return xmlrpc.client.dumps(fault, allow_none=None)

def xmlrpc_handle_exception_string(e):
    if isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpc.client.Fault('warning -- %s\n\n%s' % (e.name, e.value), '')
    elif isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpc.client.Fault('warning -- Warning\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.MissingError):
        fault = xmlrpc.client.Fault('warning -- MissingError\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.AccessError):
        fault = xmlrpc.client.Fault('warning -- AccessError\n\n' + str(e), '')
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpc.client.Fault('AccessDenied', str(e))
    elif isinstance(e, odoo.exceptions.DeferredException):
        info = e.traceback
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpc.client.Fault(odoo.tools.ustr(e), formatted_info)
    #InternalError
    else:
        info = sys.exc_info()
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpc.client.Fault(odoo.tools.exception_to_unicode(e), formatted_info)

    return xmlrpc.client.dumps(fault, allow_none=None, encoding=None)

class OdooMarshaller(xmlrpc.client.Marshaller):

    dispatch = dict(xmlrpc.client.Marshaller.dispatch)

    # By default, in xmlrpc, bytes are converted to xmlrpc.client.Binary object.
    # Historically, odoo is sending binary as base64 string.
    # In python 3, base64.b64{de,en}code() methods now works on bytes.
    # Convert them to str to have a consistent behavior between python 2 and python 3.
    # TODO? Create a `/xmlrpc/3` route prefix that respect the standard and uses xmlrpc.client.Binary.
    def dump_bytes(marshaller, value, write):
        marshaller.dump_unicode(odoo.tools.ustr(value), write)
    dispatch[bytes] = dump_bytes

    # convert datetime objects to strings in iso8061 format.
    def dump_datetime(self, value, write):
        # override to marshall as a string for backwards compatibility
        value = Datetime.to_string(value)
        self.dump_unicode(value, write)
    dispatch[datetime] = dump_datetime

    # convert date objects to strings in iso8061 format.
    def dump_date(self, value, write):
        value = Date.to_string(value)
        self.dump_unicode(value, write)
    dispatch[date] = dump_date

    def dump_lazy(self, value, write):
        v = value._value
        return self.dispatch[type(v)](self, v, write)
    dispatch[lazy] = dump_lazy

    # 2many commands helpers are just aliases to int
    dispatch[Command] = dispatch[int]


# monkey-patch xmlrpc.client's marshaller
xmlrpc.client.Marshaller = OdooMarshaller

#-----------------------------------------------------------
# RPC Controller
#-----------------------------------------------------------
class RPC(Controller):
    """Handle RPC connections."""

    def _xmlrpc(self, service):
        """Common method to handle an XML-RPC request."""
        data = request.httprequest.get_data()
        params, method = xmlrpc.client.loads(data)
        result = request.rpc_dispatch(service, method, params)
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
        return request.rpc_dispatch(service, method, args)

#

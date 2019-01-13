from datetime import date, datetime
from xmlrpc.client import dumps, loads
import xmlrpc.client

from werkzeug.wrappers import Response

from odoo.http import Controller, dispatch_rpc, request, route
from odoo.service import wsgi_server
from odoo.fields import Date, Datetime


class OdooMarshaller(xmlrpc.client.Marshaller):

    """
    XMLRPC Marshaller that converts date(time) objects to strings in iso8061 format.
    """

    dispatch = dict(xmlrpc.client.Marshaller.dispatch)

    def dump_datetime(self, value, write):
        # override to marshall as a string for backwards compatibility
        value = Datetime.to_string(value)
        self.dump_unicode(value, write)
    dispatch[datetime] = dump_datetime

    def dump_date(self, value, write):
        value = Date.to_string(value)
        self.dump_unicode(value, write)
    dispatch[date] = dump_date


# monkey-patch xmlrpc.client's marshaller
xmlrpc.client.Marshaller = OdooMarshaller


class RPC(Controller):
    """Handle RPC connections."""

    def _xmlrpc(self, service):
        """Common method to handle an XML-RPC request."""
        data = request.httprequest.get_data()
        params, method = loads(data)
        result = dispatch_rpc(service, method, params)
        return dumps((result,), methodresponse=1, allow_none=False)

    @route("/xmlrpc/<service>", auth="none", method="POST", csrf=False, save_session=False)
    def xmlrpc_1(self, service):
        """XML-RPC service that returns faultCode as strings.

        This entrypoint is historical and non-compliant, but kept for
        backwards-compatibility.
        """
        try:
            response = self._xmlrpc(service)
        except Exception as error:
            response = wsgi_server.xmlrpc_handle_exception_string(error)
        return Response(response=response, mimetype='text/xml')

    @route("/xmlrpc/2/<service>", auth="none", method="POST", csrf=False, save_session=False)
    def xmlrpc_2(self, service):
        """XML-RPC service that returns faultCode as int."""
        try:
            response = self._xmlrpc(service)
        except Exception as error:
            response = wsgi_server.xmlrpc_handle_exception_int(error)
        return Response(response=response, mimetype='text/xml')

    @route('/jsonrpc', type='json', auth="none", save_session=False)
    def jsonrpc(self, service, method, args):
        """ Method used by client APIs to contact OpenERP. """
        return dispatch_rpc(service, method, args)

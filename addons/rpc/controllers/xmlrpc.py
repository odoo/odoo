import logging
import traceback
import xmlrpc.client
from collections import defaultdict
from datetime import date, datetime

from markupsafe import Markup

import odoo.exceptions
from odoo.fields import Command, Date, Datetime
from odoo.http import Controller, Response, dispatch_rpc, request, route
from odoo.tools import lazy
from odoo.tools.misc import ReadonlyDict, frozendict

from .common import detach_database, warn_endpoint_is_deprecated

logger = logging.getLogger(__name__)

RPC_FAULT_CODE_APPLICATION_ERROR = 1
RPC_FAULT_CODE_WARNING = 2
RPC_FAULT_CODE_ACCESS_DENIED = 3
RPC_FAULT_CODE_ACCESS_ERROR = 4

CONTROL_CHARACTERS = dict.fromkeys(set(range(32)) - {9, 10, 13})


def _format_traceback(e: BaseException) -> str:
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))


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
        fault = xmlrpc.client.Fault(
            RPC_FAULT_CODE_APPLICATION_ERROR, _format_traceback(e)
        )

    return dumps(fault)


def xmlrpc_handle_exception_string(e):
    if isinstance(e, odoo.exceptions.RedirectWarning):
        fault = xmlrpc.client.Fault(f"warning -- Warning\n\n{e}", "")
    elif isinstance(e, odoo.exceptions.MissingError):
        fault = xmlrpc.client.Fault(f"warning -- MissingError\n\n{e}", "")
    elif isinstance(e, odoo.exceptions.AccessError):
        fault = xmlrpc.client.Fault(f"warning -- AccessError\n\n{e}", "")
    elif isinstance(e, odoo.exceptions.AccessDenied):
        fault = xmlrpc.client.Fault("AccessDenied", str(e))
    elif isinstance(e, odoo.exceptions.UserError):
        fault = xmlrpc.client.Fault(f"warning -- UserError\n\n{e}", "")
    else:
        fault = xmlrpc.client.Fault(str(e), _format_traceback(e))

    return dumps(fault)


class _MarshallerDispatch(dict):
    def __missing__(self, cls):
        if isinstance(cls, type) and issubclass(cls, ReadonlyDict):
            handler = self[cls] = dict.__getitem__(self, ReadonlyDict)
            return handler
        raise KeyError(cls)


class OdooMarshaller(xmlrpc.client.Marshaller):
    dispatch = _MarshallerDispatch(xmlrpc.client.Marshaller.dispatch)

    def dump_frozen_dict(self, value, write):
        value = dict(value)
        self.dump_struct(value, write)

    def dump_bytes(self, value, write):
        self.dump_unicode(value.decode(), write)

    def dump_datetime(self, value, write):
        value = Datetime.to_string(value)
        self.dump_unicode(value, write)

    def dump_date(self, value, write):
        value = Date.to_string(value)
        self.dump_unicode(value, write)

    def dump_lazy(self, value, write):
        return self._Marshaller__dump(value._value, write)

    def dump_unicode(self, value, write):
        return super().dump_unicode(value.translate(CONTROL_CHARACTERS), write)

    dispatch[frozendict] = dump_frozen_dict
    dispatch[ReadonlyDict] = dump_frozen_dict
    dispatch[bytes] = dump_bytes
    dispatch[datetime] = dump_datetime
    dispatch[date] = dump_date
    dispatch[lazy] = dump_lazy
    dispatch[str] = dump_unicode
    dispatch[Command] = dispatch[int]
    dispatch[defaultdict] = dispatch[dict]
    dispatch[Markup] = lambda self, value, write: self.dispatch[str](
        self, str(value), write
    )


def dumps(params: list | tuple | xmlrpc.client.Fault) -> str:
    response = OdooMarshaller(allow_none=False).dumps(params)
    return f"""\
<?xml version="1.0"?>
<methodResponse>
{response}
</methodResponse>
"""


class XMLRPC(Controller):
    def _xmlrpc(self, service):
        data = request.httprequest.get_data()
        params, method = xmlrpc.client.loads(data, use_datetime=True)
        result = dispatch_rpc(service, method, params)
        return dumps((result,))

    @route(
        "/xmlrpc/<service>",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def xmlrpc_1(self, service):  # noqa: E8528 - the XML-RPC API, authenticated per call by the credentials it carries
        warn_endpoint_is_deprecated(logger, __name__)
        detach_database()
        try:
            response = self._xmlrpc(service)
        except Exception as error:
            error.error_response = Response(
                response=xmlrpc_handle_exception_string(error),
                mimetype="text/xml",
            )
            raise
        return Response(response=response, mimetype="text/xml")

    @route(
        "/xmlrpc/2/<service>",
        auth="none",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def xmlrpc_2(self, service):  # noqa: E8528 - the XML-RPC API, authenticated per call by the credentials it carries
        warn_endpoint_is_deprecated(logger, __name__)
        detach_database()
        try:
            response = self._xmlrpc(service)
        except Exception as error:
            error.error_response = Response(
                response=xmlrpc_handle_exception_int(error),
                mimetype="text/xml",
            )
            raise
        return Response(response=response, mimetype="text/xml")

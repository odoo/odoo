import encodings
import logging
import re
import socket
import sys
import threading
import traceback
import xmlrpc.client
from datetime import date, datetime
from http import HTTPStatus
from json.decoder import JSONDecodeError
from xml.parsers.expat import ExpatError

from markupsafe import Markup
from werkzeug.exceptions import (
    HTTPException, Unauthorized, Forbidden, NotFound, UnsupportedMediaType,
    abort
)
from werkzeug.wrappers import Response

import odoo
from odoo.exceptions import AccessDenied
from odoo.fields import Date, Datetime, Command
from odoo.http import (
    dispatch_rpc, serialize_exception, Controller, route, request,
    borrow_request,
)
from odoo.tools import frozendict, lazy, unique, ustr

from .rpc2.exceptions import RpcError, RpcErrorCode
from .rpc2.marshaller import XMLRPCMarshaller, JSONMarshaller
from .rpc2.admin import dispatch as admin_dispatch
from .rpc2.model import dispatch as model_dispatch

_logger = logging.getLogger(__name__)


# ==========================================================
# Deprecated /xmlrpc, /xmlrpc/2, /jsonrpc and helpers
# ==========================================================
_XMLRPC_DEPRECATION_WARNING = """Deprecation Warning!

The /xmlrpc and /xmlrpc/2 endpoints are deprecated but are still used
by a client at %s [%s]. Please report them the problem
with the following notice:

The two Odoo XMLRPC endpoints at /xmlrpc and /xmlrpc/2 are deprecated
since version 17 (autumn 2023) and are scheduled for removal. The two
endpoints have been replaced by a new unique one: /RPC2. This new url
offers a better integration with XMLRPC libraries:

* support for HTTP Basic-Authentication;
* support of the None/null/nil value;
* support of dot-name function notation (see below);
* enhanced support for the "new" (Odoo 8) ORM API.

Using python's xmlrpc client and previous endpoint, you used to do:

    common = xmlrpc.client.ServerProxy(f'https://{domain}/xmlrpc/2/common')
    uid = common.authenticate(db, username, password, {})
    models = xmlrpc.client.ServerProxy(f'https://{domain}/xmlrpc/2/object')
    models.execute_kw(db, uid, password, 'res.partner', 'read', ...)

With the new /RPC2 endpoint, you do:

    url = f'https://{username}:{password}@{domain}/RPC/{db}'
    models = xmlrpclib.ServerProxy(url)
    models.res.partner.read(...)

Several others XML-RPC and JSON-RPC clients libraries from a multitude
for different languages benefit too from this shorter syntax. A complete
tutorial that includes currated examples for many languages is available
in the "External API" section of the Odoo Online Documentation.

https://www.odoo.com/documentation/16.0/developer/api/external_api.html
"""

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

    return fault


def xmlrpc_handle_exception_string(e):
    """ Legacy converter: historically Odoo has mis-generated XML-RPC fault by
    using a ``<string>`` as the ``<faultCode>`` even though it must be an
    ``<int>``.
    This function provides the old (incorrect) behavior where
    :func:`~.xmlrpc_handle_exception_int` implements the correct behavior of
    integral ``<faultCode>``
    """
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
    else:
        info = sys.exc_info()
        formatted_info = "".join(traceback.format_exception(*info))
        fault = xmlrpc.client.Fault(odoo.tools.exception_to_unicode(e), formatted_info)

    return xmlrpc.client.dumps(fault)


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
        # Famous event that occured in 2013:
        # * Edward Snowden leaked the NSA secrets;
        # * Francis was elected Pope;
        # * Antony Lesuisse deprecated this route.
        _logger.warning(
            _XMLRPC_DEPRECATION_WARNING,
            socket.getnameinfo((request.httprequest.remote_addr, 0), 0)[0],
            request.httprequest.remote_addr,
        )
        try:
            response = self._xmlrpc(service)
        except Exception as error:
            response = xmlrpc_handle_exception_string(error)
        return Response(response=response, mimetype='text/xml')

    @route("/xmlrpc/2/<service>", auth="none", methods=["POST"], csrf=False, save_session=False)
    def xmlrpc_2(self, service):
        """XML-RPC service that returns faultCode as int."""
        _logger.warning(
            _XMLRPC_DEPRECATION_WARNING,
            socket.getnameinfo((request.httprequest.remote_addr, 0), 0)[0],
            request.httprequest.remote_addr,
        )
        try:
            response = self._xmlrpc(service)
        except Exception as error:
            response = xmlrpc.client.dumps(xmlrpc_handle_exception_int(error))
        return Response(response=response, mimetype='text/xml')

    @route('/jsonrpc', type='json', auth="none", save_session=False)
    def jsonrpc(self, service, method, args):
        """ Method used by client APIs to contact OpenERP. """
        return dispatch_rpc(service, method, args)


# ==========================================================
# New RPC endpoint
# ==========================================================
ACCEPT_CHARSET = ', '.join(
    'application/json; charset={0}, text/xml; charset={0}'.format(
        charset.replace('_', '-')
    ) for charset in unique(encodings.aliases.aliases.values())
)

class Rpc2(Controller):
    # python's <3.9 xmlrpc client doesn't send query-strings, hence the /RPC2/<db> route
    # https://github.com/python/cpython/commit/5334605035d38139a04189ecb3899f36702517b2
    @route(['/RPC2', '/RPC2/<db>'], auth='none', methods=['POST'], csrf=False)
    def rpc2(self, db=None):
        req = request.httprequest

        # by default werkzeug decode the request using utf-8, use the
        # real charset of the request instead (falling back on utf-8)
        req.charset = req.mimetype_params.get('charset', req.charset)
        req.encoding_errors = 'strict'

        if db and db not in odoo.http.db_list([db]):
            raise NotFound("Database not found")

        if req.mimetype == 'text/xml':
            return Response(
                (b"<?xml version='1.0'?>\n<methodResponse>%s</methodResponse>\n"
                    % XMLRPCMarshaller('utf-8').dumps(self._xmlrpc(db))),
                mimetype='text/xml'
            )
        elif req.mimetype == 'application/json':
            return Response(
                JSONMarshaller(ensure_ascii=False).encode(self._jsonrpc(db)),
                mimetype='application/json; charset=utf-8'
            )

        resp = UnsupportedMediaType(
            f"{req.mimetype} mime type not supported by /RPC2, request may "
            "be either XML-RPC as text/xml or JSON-RPC 2.0 as application/json."
        ).get_response()
        resp.headers['Accept'] = ACCEPT_CHARSET
        abort(resp)


    def _xmlrpc(self, db):
        try:
            try:
                params, method = xmlrpc.client.loads(request.httprequest.get_data(as_text=True))
            except LookupError as exc:
                request.future_response.status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
                request.future_response.headers['Accept'] = ACCEPT_CHARSET
                raise RpcError(RpcErrorCode.unsupported_encoding) from exc
            except UnicodeDecodeError as exc:
                request.future_response.status = HTTPStatus.BAD_REQUEST
                raise RpcError(RpcErrorCode.encoding_error) from exc
            except ExpatError as exc:
                request.future_response.status = HTTPStatus.BAD_REQUEST
                raise RpcError(RpcErrorCode.parse_error) from exc
            except Exception as exc1:
                request.future_response.status = HTTPStatus.BAD_REQUEST
                exc2 = ValueError("malformed XML-RPC request")
                exc2.__cause__ = exc1
                raise RpcError(RpcErrorCode.invalid_request) from exc2
            try:
                return (self._dispatch(db, method, params),)
            except HTTPException:
                raise
            except RpcError:
                raise
            except Exception as exc:
                _logger.exception("Exception during XMLRPC request handling.")
                raise RpcError(RpcErrorCode.from_exception(exc)) from exc
        except RpcError as rpc_error:
            return xmlrpc.client.Fault(
                faultCode=int(rpc_error.code),
                faultString=''.join(traceback.format_exception_only(rpc_error.__cause__)).strip()
            )

    def _jsonrpc(self, db):
        try:
            jsonreq = {}
            try:
                jsonreq.update(request.get_json_data())
                id_ = jsonreq['id']
                method = jsonreq['method']
                params = jsonreq.get('params', [])
            except LookupError as exc:
                request.future_response.status = HTTPStatus.UNSUPPORTED_MEDIA_TYPE
                request.future_response.headers['Accept'] = ACCEPT_CHARSET
                raise RpcError(RpcErrorCode.unsupported_encoding) from exc
            except UnicodeDecodeError as exc:
                request.future_response.status = HTTPStatus.BAD_REQUEST
                raise RpcError(RpcErrorCode.encoding_error) from exc
            except JSONDecodeError as exc:
                request.future_response.status = HTTPStatus.BAD_REQUEST
                raise RpcError(RpcErrorCode.parse_error) from exc
            except Exception as exc1:
                request.future_response.status = HTTPStatus.BAD_REQUEST
                exc2 = ValueError("malformed JSON-RPC request")
                exc2.__cause__ = exc1
                raise RpcError(RpcErrorCode.invalid_request) from exc2
            try:
                return {
                    'jsonrpc': '2.0',
                    'id': id_,
                    'result': self._dispatch(db, method, params)
                }
            except HTTPException:
                raise
            except RpcError:
                raise
            except Exception as exc:
                _logger.exception("Exception during JSONRPC request handling.")
                raise RpcError(RpcErrorCode.from_exception(exc)) from exc
        except RpcError as rpc_error:
            return {
                'jsonrpc': '2.0',
                'id': jsonreq.get('id'),
                'error': {
                    'code': int(rpc_error.code),
                    'message': ''.join(traceback.format_exception_only(rpc_error.__cause__)).strip(),
                    'data': serialize_exception(rpc_error.__cause__)
                }
            }

    def _dispatch(self, db, method, params):
        model, _, method = method.rpartition('.')
        auth = request.httprequest.authorization
        if not db and model:
            raise RpcError(RpcErrorCode.method_not_found) from (
                NameError(f"{model+'.'+method!r} is not a valid admin function"))
        if db and not model:
            raise RpcError(RpcErrorCode.method_not_found) from (
                NameError(f"{method!r} is not a valid model name"))

        with borrow_request():
            if not db:
                try:
                    pwd = auth.password if auth else None
                    return admin_dispatch(method, *params, admin_password=pwd)
                except AccessDenied as exc:
                    if not auth or auth.type != 'basic':
                        response = Response(status=401)
                        response.www_authenticate.set_basic("Odoo-RPC")
                        raise Unauthorized(response=response) from exc
                    raise Forbidden(exc.args[0]) from exc

            if not auth or auth.type != 'basic':
                response = Response(status=401)
                response.www_authenticate.set_basic("Odoo-RPC")
                raise Unauthorized(response=response)

            registry = odoo.registry(db)
            registry.check_signaling()
            try:
                uid = registry['res.users'].authenticate(
                    db, auth.username, auth.password, {'interactive': False})
            except AccessDenied as exc:
                raise Forbidden(exc.args[0]) from exc

            threading.current_thread().uid = uid
            threading.current_thread().dbname = db

            with registry.manage_changes():
                return model_dispatch(registry, uid, model, method, *params)

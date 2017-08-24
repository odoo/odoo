# -*- coding: utf-8 -*-
import base64
import collections
import json
import logging
import threading
import types
from datetime import datetime
try:
    from xmlrpc import client as xmlrpclib
except ImportError:
    import xmlrpclib

import werkzeug.exceptions
import werkzeug.wrappers
from lxml import etree
from lxml.builder import E

from odoo import http, models, service, registry
from odoo.service import security

from . import global_, database, model
from . import models

logger = logging.getLogger(__name__)


class Rpc2(http.Controller):
    @http.route('/RPC2/', auth='none', methods=['POST'], csrf=False)
    def rpc2(self, db=None):
        req = http.request.httprequest

        if req.mimetype == 'text/xml':
            marshaller = lambda result:(
                "<?xml version='1.0'?>\n"
                "<methodResponse>%s</methodResponse>\n" %
                    XMLRPCMarshaller('utf-8').dumps((result,))
            )
            try:
                params, method = xmlrpclib.loads(req.stream.read())
                result = self.dispatch(db, method, params)
                response = marshaller(result)
            except NameError as e:
                response = marshaller(xmlrpclib.Fault(
                    faultCode=xmlrpclib.METHOD_NOT_FOUND,
                    faultString=str(e)
                ))
            except xmlrpclib.Fault as f:
                response = marshaller(f)
            except Exception as e:
                response = service.wsgi_server.xmlrpc_convert_exception_int(e)
        elif req.mimetype == 'application/json':
            request = {}
            try:
                request = json.load(req.stream)
                assert 'id' in request, "Notification requests are not supported"
                result = self.dispatch(
                    db, request['method'], request.get('params', []))
                resp = {
                    'jsonrpc': '2.0',
                    'id': request['id'],
                    'result': result
                }
            except Exception as e:
                resp = {
                    'jsonrpc': '2.0',
                    'id': request.get('id'),
                    'error': {
                        # TODO: use XML-RPC fault codes from wsgi_server?
                        'code': 200,
                        'message': str(e),
                        'data': http.serialize_exception(e)
                    }
                }
            response = JSONMarshaller().encode(resp)
        else:
            return werkzeug.exceptions.UnsupportedMediaType(
                "%s mime type not supported by /RPC2, request may be either "
                "XML-RPC as text/xml or JSON-RPC 2.0 as application/json"
                % req.mimetype)

        return werkzeug.wrappers.Response(response, mimetype=req.mimetype)

    def dispatch(self, db, method, params):
        path = method.split('.')
        if not db:
            if len(path) != 1:
                raise NameError("{} is not a valid global method".format(method))
            [func] = path
            return global_.dispatch(func, *params)

        uid = None
        auth = http.request.httprequest.authorization
        if auth and auth.type == 'basic':
            uid = security.login(db, auth.username, auth.password)

        if not uid:
            r = werkzeug.wrappers.Response(status=401)
            r.www_authenticate.set_basic("Odoo-RPC")
            raise werkzeug.exceptions.Unauthorized(response=r)

        threading.current_thread().uid = uid
        threading.current_thread().dbname = db


        r = registry(db).check_signaling()
        try:
            if len(path) == 1:
                return database.dispatch(r, uid, path[0], *params)
            else:
                model_name, func = method.rsplit('.', 1)
                return model.dispatch(r, uid, model_name, func, *params)
        finally:
            r.signal_changes()

class Dispatcher(object):
    """ Dispatches values to instance methods based on value types

    >>> class A(object):
    ...     dispatcher = Dispatcher()
    ...     @dispatcher.register(int)
    ...     def _int(self, value):
    ...         return "int {}".format(value)
    ...     @dispatcher.register(float)
    ...     def _float(self, value):
    ...         return "float {}".format(value)
    >>> a = A()
    >>> a.dispatcher(1)
    'int 1'
    >>> a.dispatcher(1.)
    'float 1.0'
    """
    def __init__(self):
        self.types = []
        self.default = None

    def register(self, types):
        def decorator(fn):
            self.types.append((types, fn))
            return fn
        return decorator
    def register_default(self, default):
        self.default = default

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return Proxy(self, instance)
    def __call__(self): pass

class XMLRPCMarshaller(object):
    serialize = Dispatcher()
    def __init__(self, encoding='utf-8'):
        self.encoding = encoding
        self.memo = set()
    def dumps(self, values):
        if isinstance(values, xmlrpclib.Fault):
            tree = E.fault(self.serialize({
                'faultCode': values.faultCode,
                'faultString': values.faultString,
            }))
        else:
            tree = E.params()
            tree.extend(E.param(self.serialize(value)) for value in values)
        return etree.tostring(tree, encoding=self.encoding, xml_declaration=False)

    @serialize.register(models.BaseModel)
    def dump_model(self, value):
        return self.serialize(value.ids)

    @serialize.register(types.NoneType)
    def dump_none(self, value):
        return E.value(E.nil())

    @serialize.register(bool)
    def dump_bool(self, value):
        return E.value(E.boolean("1" if value else "0"))

    @serialize.register((int, long))
    def dump_int(self, value):
        if value > xmlrpclib.MAXINT or value < xmlrpclib.MININT:
            raise OverflowError("int exceeds XML-RPC limits")
        return E.value(E.int(str(value)))

    @serialize.register(float)
    def dump_float(self, value):
        return E.value(E.double(repr(value)))

    # fixme: string_types?
    @serialize.register(basestring)
    def dump_str(self, value):
        return E.value(E.string(value))

    @serialize.register(collections.Mapping)
    def dump_mapping(self, value):
        m = id(value)
        if m in self.memo:
            raise TypeError("cannot marshal recursive dictionaries")
        self.memo.add(m)
        struct = E.struct()
        struct.extend(
            # coerce all keys to string (same as JSON)
            E.member(E.name(unicode(k)), self.serialize(v))
            for k, v in value.iteritems()
        )
        self.memo.remove(m)
        return E.value(struct)

    @serialize.register(collections.Iterable)
    def dump_iterable(self, value):
        m = id(value)
        if m in self.memo:
            raise TypeError("cannot marshal recursive sequences")
        self.memo.add(m)
        data = E.data()
        data.extend(self.serialize(v) for v in value)
        self.memo.remove(m)
        return E.value(E.array(data))

    @serialize.register(datetime)
    def dump_datetime(self, value):
        d = etree.Element('datetime.iso8601')
        d.text = value.replace(microsecond=0).isoformat()
        return E.value(d)

    # FIXME: bytes in p3 but not in p2?
    @serialize.register(xmlrpclib.Binary)
    def dump_binary(self, value):
        return E.value(E.base64(base64.encodestring(value.data)))

    @serialize.register_default
    def fallback(self, value):
        return self.serialize(vars(value))

class JSONMarshaller(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, models.BaseModel):
            return o.ids
        if isinstance(o, collections.Mapping):
            return dict(o)
        if isinstance(o, collections.Iterable):
            return list(o)
        return super(JSONMarshaller, self).default(o)

class Proxy(object):
    def __init__(self, dispatcher, instance):
        self.dispatcher = dispatcher
        self.instance = instance
    def __call__(self, item):
        for types, fn in self.dispatcher.types:
            if isinstance(item, types):
                return fn(self.instance, item)
        return self.dispatcher.default(self.instance, item)

# -*- coding: utf-8 -*-
import json
import unittest2

from .. import http
import werkzeug.test


def setUpModule():
    """
    Force load_addons once to import all the crap we don't care for as this
    thing is full of side-effects
    """
    http.Root().load_addons()

class DispatchCleanup(unittest2.TestCase):
    """
    Cleans up controllers registries in the web client so it's possible to
    test controllers registration and dispatching in isolation.
    """
    def setUp(self):
        self.classes = http.controllers_class
        self.objects = http.controllers_object
        self.paths = http.controllers_path

        http.controllers_class = []
        http.controllers_object = {}
        http.controllers_path = {}

    def tearDown(self):
        http.controllers_path = self.paths
        http.controllers_object = self.objects
        http.controllers_class = self.classes


def jsonrpc_body(params=None):
    """
    Builds and dumps the body of a JSONRPC request with params ``params``
    """
    return json.dumps({
        'jsonrpc': '2.0',
        'method': 'call',
        'id': None,
        'params': params or {},
    })


def jsonrpc_response(result=None):
    """
    Builds a JSONRPC response (as a Python dict) with result ``result``
    """
    return {
        u'jsonrpc': u'2.0',
        u'id': None,
        u'result': result,
    }


class TestDispatching(DispatchCleanup):
    def setUp(self):
        super(TestDispatching, self).setUp()
        self.app = http.Root()
        self.client = werkzeug.test.Client(self.app)

    def test_not_exposed(self):
        class CatController(http.Controller):
            _cp_path = '/cat'

            def index(self):
                return 'Blessid iz da feline'

        self.app.load_addons()

        body, status, headers = self.client.get('/cat')
        self.assertEqual('404 NOT FOUND', status)

    def test_basic_http(self):
        class CatController(http.Controller):
            _cp_path = '/cat'

            @http.httprequest
            def index(self, req):
                return 'no walk in counsil of wickid,'

        self.app.load_addons()

        body, status, headers = self.client.get('/cat')
        self.assertEqual('200 OK', status)
        self.assertEqual('no walk in counsil of wickid,', ''.join(body))

    def test_basic_jsonrpc(self):
        class CatController(http.Controller):
            _cp_path = '/cat'

            @http.jsonrequest
            def index(self, req):
                return 'no place paws in path of da sinnerz,'
        self.app.load_addons()

        body, status, headers = self.client.post('/cat', data=jsonrpc_body())

        self.assertEqual('200 OK', status)
        self.assertEqual(
            jsonrpc_response('no place paws in path of da sinnerz,'),
            json.loads(''.join(body)))

    def test_add_method(self):
        class CatController(http.Controller):
            _cp_path = '/cat'

            @http.httprequest
            def index(self, req):
                return 'no sit and purr with da mockerz.'

        class CeilingController(CatController):
            @http.httprequest
            def lol(self, req):
                return 'But der delightz in lawz of Ceiling Cat,'

        self.app.load_addons()

        body, status, headers = self.client.get('/cat')
        self.assertEqual('200 OK', status)
        self.assertEqual('no sit and purr with da mockerz.', ''.join(body))
        body, status, headers = self.client.get('/cat/lol')
        self.assertEqual('200 OK', status)
        self.assertEqual('But der delightz in lawz of Ceiling Cat,',
                         ''.join(body))

    def test_override_method(self):
        class CatController(http.Controller):
            _cp_path = '/cat'

            @http.httprequest
            def index(self, req):
                return 'an ponderz'

        class CeilingController(CatController):
            @http.httprequest
            def index(self, req):
                return '%s much.' % super(CeilingController, self).index(req)

        self.app.load_addons()

        body, status, headers = self.client.get('/cat')
        self.assertEqual('200 OK', status)
        self.assertEqual('an ponderz much.', ''.join(body))

    def test_make_invisible(self):
        class CatController(http.Controller):
            _cp_path = '/cat'

            @http.httprequest
            def index(self, req):
                return 'Tehy liek treez bai teh waterz,'

        class CeilingController(CatController):
            def index(self, req):
                return super(CeilingController, self).index(req)

        self.app.load_addons()

        body, status, headers = self.client.get('/cat')
        self.assertEqual('404 NOT FOUND', status)

    def test_make_json_invisible(self):
        class CatController(http.Controller):
            _cp_path = '/cat'

            @http.jsonrequest
            def index(self, req):
                return 'Tehy liek treez bai teh waterz,'

        class CeilingController(CatController):
            def index(self, req):
                return super(CeilingController, self).index(req)

        self.app.load_addons()

        body, status, headers = self.client.post('/cat')
        self.assertEqual('404 NOT FOUND', status)

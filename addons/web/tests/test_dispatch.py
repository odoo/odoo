# -*- coding: utf-8 -*-
import contextlib
import json
import logging
import logging.handlers
import types
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
        self.paths = http.controllers_path

        http.controllers_class = {}
        http.controllers_path = {}

    def tearDown(self):
        http.controllers_path = self.paths
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


class TestHandler(logging.handlers.BufferingHandler):
    def __init__(self):
        logging.handlers.BufferingHandler.__init__(self, 0)

    def shouldFlush(self, record):
        return False

@contextlib.contextmanager
def capture_logging(logger, level=logging.DEBUG):
    logger = logging.getLogger(logger)
    old_level = logger.level
    old_handlers = logger.handlers
    old_propagate = logger.propagate

    test_handler = TestHandler()
    logger.handlers = [test_handler]
    logger.setLevel(level)
    logger.propagate = False

    try:
        yield test_handler
    finally:
        logger.propagate = old_propagate
        logger.setLevel(old_level)
        logger.handlers = old_handlers


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


class TestSubclassing(DispatchCleanup):
    def setUp(self):
        super(TestSubclassing, self).setUp()
        self.app = http.Root()
        self.client = werkzeug.test.Client(self.app)

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

    def test_extends(self):
        """
        When subclassing an existing Controller new classes are "merged" into
        the base one
        """
        class A(http.Controller):
            _cp_path = '/foo'
            @http.httprequest
            def index(self, req):
                return '1'

        class B(A):
            @http.httprequest
            def index(self, req):
                return "%s 2" % super(B, self).index(req)

        class C(A):
            @http.httprequest
            def index(self, req):
                return "%s 3" % super(C, self).index(req)

        self.app.load_addons()

        body, status, headers = self.client.get('/foo')
        self.assertEqual('200 OK', status)
        self.assertEqual('1 2 3', ''.join(body))

    def test_extends_same_path(self):
        """
        When subclassing an existing Controller and specifying the same
        _cp_path as the parent, ???
        """
        class A(http.Controller):
            _cp_path = '/foo'
            @http.httprequest
            def index(self, req):
                return '1'

        class B(A):
            _cp_path = '/foo'
            @http.httprequest
            def index(self, req):
                return '2'

        self.app.load_addons()

        body, status, headers = self.client.get('/foo')
        self.assertEqual('200 OK', status)
        self.assertEqual('2', ''.join(body))

    def test_re_expose(self):
        """
        An existing Controller should not be extended with a new cp_path
        (re-exposing somewhere else)
        """
        class CatController(http.Controller):
            _cp_path = '/cat'

            @http.httprequest
            def index(self, req):
                return '[%s]' % self.speak()

            def speak(self):
                return 'Yu ordered cheezburgerz,'

        with capture_logging('openerp.addons.web.http') as handler:
            class DogController(CatController):
                _cp_path = '/dog'

                def speak(self):
                    return 'Woof woof woof woof'

            [record] = handler.buffer
            self.assertEqual(logging.WARN, record.levelno)
            self.assertEqual("Re-exposing CatController at /dog.\n"
                             "\tThis usage is unsupported.",
                             record.getMessage())

    def test_fail_redefine(self):
        """
        An existing Controller can't be overwritten by a new one on the same
        path (? or should this generate a warning and still work as if it was
        an extend?)
        """
        class FooController(http.Controller):
            _cp_path = '/foo'

        with self.assertRaises(AssertionError):
            class BarController(http.Controller):
                _cp_path = '/foo'

    def test_fail_no_path(self):
        """
        A Controller must have a path (and thus be exposed)
        """
        with self.assertRaises(AssertionError):
            class FooController(http.Controller):
                pass

    def test_mixin(self):
        """
        Can mix "normal" python classes into a controller directly
        """
        class Mixin(object):
            @http.httprequest
            def index(self, req):
                return 'ok'

        class FooController(http.Controller, Mixin):
            _cp_path = '/foo'

        class BarContoller(Mixin, http.Controller):
            _cp_path = '/bar'

        self.app.load_addons()

        body, status, headers = self.client.get('/foo')
        self.assertEqual('200 OK', status)
        self.assertEqual('ok', ''.join(body))

        body, status, headers = self.client.get('/bar')
        self.assertEqual('200 OK', status)
        self.assertEqual('ok', ''.join(body))

    def test_mixin_extend(self):
        """
        Can mix "normal" python class into a controller by extension
        """
        class FooController(http.Controller):
            _cp_path = '/foo'

        class M1(object):
            @http.httprequest
            def m1(self, req):
                return 'ok 1'

        class M2(object):
            @http.httprequest
            def m2(self, req):
                return 'ok 2'

        class AddM1(FooController, M1):
            pass

        class AddM2(M2, FooController):
            pass

        self.app.load_addons()

        body, status, headers = self.client.get('/foo/m1')
        self.assertEqual('200 OK', status)
        self.assertEqual('ok 1', ''.join(body))

        body, status, headers = self.client.get('/foo/m2')
        self.assertEqual('200 OK', status)
        self.assertEqual('ok 2', ''.join(body))

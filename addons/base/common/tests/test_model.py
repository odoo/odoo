# -*- coding: utf-8 -*-
import cherrypy
import mock
import unittest2
import openerpweb.openerpweb

class OpenERPModelTest(unittest2.TestCase):
    def test_rpc_call(self):
        session = mock.Mock(['execute'])
        Model = openerpweb.openerpweb.OpenERPModel(
            session, 'a.b')

        Model.search([('field', 'op', 'value')], {'key': 'value'})
        session.execute.assert_called_once_with(
            'a.b', 'search', [('field', 'op', 'value')], {'key': 'value'})

        session.execute.reset_mock()
        
        Model.read([42])
        session.execute.assert_called_once_with(
            'a.b', 'read', [42])

class FakeController(object):
    pass

class DispatcherTest(unittest2.TestCase):
    def setUp(self):
        controller = FakeController()
        self.mock_method = mock.Mock()
        controller.method = self.mock_method
        self.mock_method.exposed = True

        self.mock_index = mock.Mock()
        controller.index = self.mock_index
        self.mock_index.exposed = True

        self.patcher = mock.patch.dict(
            openerpweb.openerpweb.controllers_path,
            {'/some/controller/path': controller})
        self.patcher.start()

        controller2 = FakeController()
        controller2.index = self.mock_index
        self.patcher2 = mock.patch.dict(
            openerpweb.openerpweb.controllers_path,
            {'/some/other/controller': FakeController(),
             '/some/other/controller/2': controller2})
        self.patcher2.start()
    def tearDown(self):
        self.patcher2.stop()
        self.patcher.stop()

    def test_default_redirect(self):
        self.assertRaises(
            cherrypy.HTTPRedirect,
            openerpweb.openerpweb.Root().find_handler)
    def test_serve_static_missing(self):
        self.assertRaises(
            cherrypy.NotFound,
            openerpweb.openerpweb.Root().find_handler,
            'does-not-exist', 'static', 'bar')

    def test_serve_controller_missing(self):
        self.assertRaises(
            cherrypy.NotFound,
            openerpweb.openerpweb.Root().find_handler,
            'controller', 'does', 'not', 'exist')

    def test_find_controller_method(self):
        openerpweb.openerpweb.Root().find_handler(
            'some', 'controller', 'path', 'method')
        self.mock_method.assert_called_once_with()
    def test_find_controller_index(self):
        openerpweb.openerpweb.Root().find_handler(
            'some', 'controller', 'path')
        self.mock_index.assert_called_once_with()

    def test_nested_paths(self):
        openerpweb.openerpweb.Root().find_handler(
            'some', 'other', 'controller', '2')
        self.mock_index.assert_called_once_with()

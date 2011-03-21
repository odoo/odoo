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

class DispatcherTest(unittest2.case.TestCase):
    def test_default_redirect(self):
        self.assertRaises(
            cherrypy.HTTPRedirect,
            openerpweb.openerpweb.Root().default)
    def test_serve_static_missing(self):
        self.assertRaises(
            cherrypy.NotFound,
            openerpweb.openerpweb.Root().default,
            'does-not-exist', 'static', 'bar')
    def test_serve_controller_missing(self):
        self.assertRaises(
            cherrypy.NotFound,
            openerpweb.openerpweb.Root().default,
            'controller', 'does', 'not', 'exist')


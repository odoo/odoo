# -*- coding: utf-8 -*-
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

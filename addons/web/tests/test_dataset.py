# -*- coding: utf-8 -*-
import mock
import unittest2
import openerp.addons.web.controllers.main
from openerp.addons.web.http import request as req
from openerp.addons.web.http import set_request

class TestDataSetController(unittest2.TestCase):
    def setUp(self):
        self.dataset = openerp.addons.web.controllers.main.DataSet()
        self.tmp_req = set_request(mock.Mock())
        self.tmp_req.__enter__()
        self.read = req.session.model().read
        self.search = req.session.model().search

    def tearDown(self):
        self.tmp_req.__exit__()

    def test_empty_find(self):
        self.search.return_value = []
        self.read.return_value = []

        self.assertEqual(
            self.dataset.do_search_read('fake.model'),
            {'records': [], 'length': 0})
        self.read.assert_called_once_with(
            [], False, req.context)

    def test_regular_find(self):
        self.search.return_value = [1, 2, 3]

        self.dataset.do_search_read('fake.model')
        self.read.assert_called_once_with(
            [1, 2, 3], False, req.context)

    def test_ids_shortcut(self):
        self.search.return_value = [1, 2, 3]
        self.read.return_value = [
            {'id': 1, 'name': 'foo'},
            {'id': 2, 'name': 'bar'},
            {'id': 3, 'name': 'qux'}
        ]

        self.assertEqual(
            self.dataset.do_search_read('fake.model', ['id']),
            {'records': [{'id': 1}, {'id': 2}, {'id': 3}], 'length': 3})
        self.assertFalse(self.read.called)

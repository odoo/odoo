# -*- coding: utf-8 -*-
from . import common

import openerp.addons.web.controllers.main
from openerp.http import request as req

class TestDataSetController(common.MockRequestCase):
    def setUp(self):
        super(TestDataSetController, self).setUp()
        self.dataset = openerp.addons.web.controllers.main.DataSet()
        self.read = req.session.model().read
        self.search = req.session.model().search

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

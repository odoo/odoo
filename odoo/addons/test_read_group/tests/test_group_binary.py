# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import common


class TestGroupBinary(common.TransactionCase):

    def setUp(self):
        super(TestGroupBinary, self).setUp()
        self.Model = self.env['test_read_group.on_binary']

    def test_groupby_binary(self):
        with self.assertRaises(UserError):
            self.Model.read_group([], ['file'], ['file'])

    def test_groupby_func_binary(self):
        with self.assertRaises(UserError):
            self.Model.read_group([], ['file:max'], ['file'])

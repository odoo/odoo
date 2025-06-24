# -*- coding: utf-8 -*-
from odoo.exceptions import UserError
from odoo.tests import common


class TestAttributes(common.TransactionCase):

    def test_we_cannot_add_attributes(self):
        Model = self.env['test_new_api.category']
        instance = Model.create({'name': 'Foo'})

        with self.assertRaises(AttributeError):
            instance.unknown = 42

    def test_volatile_model_name_search(self):
        Model = self.env['test_new_api.volatile.model']

        with self.assertRaises(UserError):
            Model.name_search("")

        with self.assertRaises(UserError):
            Model.search_count("")

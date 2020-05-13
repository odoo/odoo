# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestViews(TransactionCase):
    def test_infinite_inherit_loop(self):
        # Creates an infinite loop: A t-call B and A inherit from B
        View = self.env['ir.ui.view']
        first_view = View.create({
            'name': 'Test View 1',
            'type': 'qweb',
            'arch': '<div>Hello World</div>',
            'key': 'web_editor.test_first_view',
        })
        second_view = View.create({
            'name': 'Test View 2',
            'type': 'qweb',
            'arch': '<t t-call="web_editor.test_first_view"/>',
            'key': 'web_editor.test_second_view',
        })
        second_view.write({
            'inherit_id': first_view.id,
        })
        # Test for RecursionError: maximum recursion depth exceeded in this function
        View._views_get(first_view)

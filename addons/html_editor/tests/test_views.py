# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import TransactionCase


class TestViews(TransactionCase):

    def setUp(self):
        super().setUp()
        View = self.env['ir.ui.view']
        self.first_view = View.create({
            'name': 'Test View 1',
            'type': 'qweb',
            'arch': '<div>Hello World</div>',
            'key': 'html_editor.test_first_view',
        })
        self.second_view = View.create({
            'name': 'Test View 2',
            'type': 'qweb',
            'arch': '<div><t t-call="html_editor.test_first_view"/></div>',
            'key': 'html_editor.test_second_view',
        })

    def test_infinite_inherit_loop(self):
        # Creates an infinite loop: A t-call B and A inherit from B
        View = self.env['ir.ui.view']

        self.second_view.write({
            'inherit_id': self.first_view.id,
        })
        # Test for RecursionError: maximum recursion depth exceeded in this function
        View._views_get(self.first_view)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged, TransactionCase


@tagged('at_install', '-post_install')  # LEGACY at_install
class TestViews(TransactionCase):

    def setUp(self):
        super().setUp()
        Qweb = self.env['ir.qweb']
        self.first_view = Qweb.create({
            'name': 'Test View 1',
            'arch': '<div>Hello World</div>',
            'key': 'html_editor.test_first_view',
        })
        self.second_view = Qweb.create({
            'name': 'Test View 2',
            'arch': '<div><t t-call="html_editor.test_first_view"/></div>',
            'key': 'html_editor.test_second_view',
        })

    def test_infinite_inherit_loop(self):
        # Creates an infinite loop: A t-call B and A inherit from B
        View = self.env['ir.qweb']

        self.second_view.write({
            'inherit_id': self.first_view.id,
        })
        # Test for RecursionError: maximum recursion depth exceeded in this function
        View._views_get(self.first_view)

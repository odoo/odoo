# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class SpreadsheetIrModel(TransactionCase):

    def test_has_searchable_parent_not_stored(self):
        self.assertEqual(self.env['ir.model'].has_searchable_parent_relation(['res.users']), {'res.users': False})

    def test_has_searchable_parent_stored(self):
        self.assertEqual(self.env['ir.model'].has_searchable_parent_relation(['ir.ui.menu']), {'ir.ui.menu': True})

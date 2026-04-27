# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase


class SpreadsheetIrModel(TransactionCase):

    def test_has_searchable_parent_not_stored(self):
        self.assertFalse(self.env['ir.model'].has_searchable_parent_relation('res.users'))

    def test_has_searchable_parent_stored(self):
        self.assertTrue(self.env['ir.model'].has_searchable_parent_relation('ir.ui.menu'))

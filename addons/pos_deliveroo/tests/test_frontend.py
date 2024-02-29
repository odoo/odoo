# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    @classmethod
    def _get_main_company(cls):
        cls.company_data["company"].country_id = cls.env.ref("base.es").id
        return cls.company_data["company"]

    def test_spanish_pos(self):
        simp = self.env['account.journal'].create({
            'name': 'Simplified Invoice Journal',
            'type': 'sale',
            'company_id': self._get_main_company().id,
            'code': 'SIMP',
        })
        def get_number_of_regular_invoices():
            return self.env['account.move'].search_count([('journal_id', '=', self.main_pos_config.invoice_journal_id.id), ('l10n_es_is_simplified', '=', False), ('pos_order_ids', '!=', False)])
        initial_number_of_regular_invoices = get_number_of_regular_invoices()
        self.main_pos_config.l10n_es_simplified_invoice_journal_id = simp
        # this `limit` value is linked to the `SIMPLIFIED_INVOICE_LIMIT` const in the tour
        self.main_pos_config.l10n_es_simplified_invoice_limit = 1000
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", "spanish_pos_tour", login="pos_user")
        num_of_simp_invoices = self.env['account.move'].search_count([('journal_id', '=', simp.id), ('l10n_es_is_simplified', '=', True)])
        num_of_regular_invoices = get_number_of_regular_invoices() - initial_number_of_regular_invoices
        self.assertEqual(num_of_simp_invoices, 3)
        self.assertEqual(num_of_regular_invoices, 1)

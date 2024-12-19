# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    @classmethod
    def _get_main_company(cls):
        cls.company_data["company"].country_id = cls.env.ref("base.es").id
        cls.company_data["company"].currency_id = cls.env.ref("base.EUR").id
        cls.company_data["company"].vat = "ESA12345674"
        return cls.company_data["company"]

    def test_spanish_tbai_pos(self):
        simp = self.env['account.journal'].create({
            'name': 'Simplified Invoice Journal',
            'type': 'sale',
            'company_id': self._get_main_company().id,
            'code': 'SIMP',
        })
        self.main_pos_config.l10n_es_simplified_invoice_journal_id = simp
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", "spanish_pos_tbai_tour", login="pos_user", debug=False)
        order = self.env['pos.order'].search([], order='id desc', limit=1)
        self.assertEqual(order.account_move.l10n_es_tbai_refund_reason, 'R1')

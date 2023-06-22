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
        self.main_pos_config.l10n_es_simplified_invoice_limit = 1000
        self.main_pos_config.l10n_es_simplified_invoice_sequence_id.prefix="test-shop-12345-"
        self.main_pos_config.with_user(self.pos_user).open_ui()
        self.start_tour(f"/pos/ui?config_id={self.main_pos_config.id}", "spanish_pos_tour", login="pos_user")
        self.assertEqual(self.main_pos_config.l10n_es_simplified_invoice_sequence_id.number_next_actual, 4)

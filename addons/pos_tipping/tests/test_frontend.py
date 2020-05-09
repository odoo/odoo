# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon

@odoo.tests.tagged('post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    def test_01_pos_tipping_acceptance(self):
        env = self.env(user=self.env.ref('base.user_admin'))

        self.main_pos_config.module_pos_restaurant = True
        self.main_pos_config.iface_start_categ_id = False
        self.main_pos_config.start_category = False

        self.main_pos_config.iface_tipproduct = True
        self.main_pos_config.tip_product_id = env['product.product'].create({
            'name': 'Tip',
            'available_in_pos': True,
            'list_price': 0,
            'taxes_id': False,
        })
        self.main_pos_config.handle_tip_adjustments = True

        floor = env['restaurant.floor'].create({
            'name': 'test floor',
            'pos_config_id': self.main_pos_config.id
        })
        env['restaurant.table'].create({
            'name': 't1',
            'floor_id': floor.id,
        })
        env['restaurant.table'].create({
            'name': 't2',
            'floor_id': floor.id,
            'position_h': 200,
        })

        # add bank journal for easy paying in acceptance tests
        bank_journal = env['account.journal'].create({
            'name': 'Bank Test',
            'type': 'bank',
            'company_id': self.env.company.id,
            'code': 'BNK',
            'sequence': 10,
        })
        self.main_pos_config.payment_method_ids |= env['pos.payment.method'].create({
            'name': 'Bank',
            'is_cash_count': False,
            'cash_journal_id': bank_journal.id,
            'receivable_account_id': self.env.company.account_default_pos_receivable_account_id.id,
        })

        # open a session, the /pos/web controller will redirect to it
        self.main_pos_config.open_session_cb(check_coa=False)

        # needed because tests are run before the module is marked as
        # installed. In js web will only load qweb coming from modules
        # that are returned by the backend in module_boot. Without
        # this you end up with js, css but no qweb.
        self.env['ir.module.module'].search([('name', '=', 'point_of_sale')], limit=1).state = 'installed'

        self.start_tour("/pos/web?config_id=%d" % self.main_pos_config.id, 'pos_tipping_acceptance', login="admin")


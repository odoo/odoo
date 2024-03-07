# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    def test_ecuadorian_pos(self):
        self.company_data["company"].country_id = self.env.ref("base.ec").id
        bank = self.main_pos_config.payment_method_ids.filtered(lambda pm: pm.name == 'Bank')[0]
        bank.l10n_ec_sri_payment_id = self.env['l10n_ec.sri.payment'].search([], limit=1)
        self.main_pos_config.with_user(self.pos_user).open_ui()
        current_session = self.main_pos_config.current_session_id
        # I create a new PoS order with 2 lines
        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_a.id,
            'pricelist_id': self.partner_a.property_product_pricelist.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.desk_pad.id,
                'price_unit': 50,
                'discount': 0,
                'qty': 1.0,
                'tax_ids': False,
                'price_subtotal': 50,
                'price_subtotal_incl': 50,
            })],
            'amount_total': 50.0,
            'amount_tax': 0.0,
            'amount_paid': 0.0,
            'amount_return': 0.0,
            'last_order_preparation_change': '{}',
            'to_invoice': True,
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': order.amount_total,
            'payment_method_id': bank.id
        })
        order_payment.with_context(**payment_context).check()
        self.assertEqual(order.account_move.l10n_ec_sri_payment_id, bank.l10n_ec_sri_payment_id, "The SRI Payment Method should be set on the invoice")

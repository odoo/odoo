# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo.addons.point_of_sale.tests.test_frontend import TestPointOfSaleHttpCommon
from odoo import Command


@odoo.tests.tagged('post_install_l10n', 'post_install', '-at_install')
class TestUi(TestPointOfSaleHttpCommon):
    @classmethod
    def _get_main_company(cls):
        cls.company_data["company"].country_id = cls.env.ref("base.ch").id
        cls.company_data["company"].currency_id = cls.env.ref("base.CHF").id
        cls.company_data["company"].vat = "CHE-530.781.296 TVA"
        return cls.company_data["company"]

    def test_l10n_ch_pos_pay_later_invoice_has_bank_partner(self):
        customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })
        self.main_pos_config.write({
            'payment_method_ids': [Command.link(customer_account_payment_method.id)],
        })
        swiss_bank = self.env['res.partner.bank'].create({
            'acc_number': 'CH11 3000 5228 1308 3501 F',
            'allow_out_payment': True,
            'partner_id': self.company.partner_id.id,
            'acc_type': 'bank',
            'bank_name': 'swiss_bank'
        })
        self.partner_test_1.write({
            "email": "test@partner1.com",
            "vat": "CHE-123.456.788 TVA",
            "contact_address_complete": "street 1, street 2, 23432 Zürich, Argovie, Switzerland"
        })
        self.main_pos_config.with_user(self.pos_admin).open_ui()
        current_session = self.main_pos_config.current_session_id

        order = self.env['pos.order'].create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner_test_1.id,
            'lines': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 10,
                'discount': 0,
                'qty': 1,
                'price_subtotal': 10,
                'price_subtotal_incl': 10,
            })],
            'amount_paid': 10.0,
            'amount_total': 10.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'to_invoice': True,
            'last_order_preparation_change': '{}'
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.env['pos.make.payment'].with_context(**payment_context).create({
            'amount': 10.0,
            'payment_method_id': customer_account_payment_method.id
        })
        order_payment.with_context(**payment_context).check()
        self.assertEqual(order.account_move.partner_bank_id, swiss_bank)

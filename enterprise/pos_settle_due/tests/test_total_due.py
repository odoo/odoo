# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

import odoo
from odoo.addons.point_of_sale.tests.common import TestPointOfSaleCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPointOfSaleFlow(TestPointOfSaleCommon):

    def test_invoicing_after_closing_session(self):
        """ Test that an invoice can be created after the session is closed """
        # create customer account payment method
        self.customer_account_payment_method = self.env['pos.payment.method'].create({
            'name': 'Customer Account',
            'split_transactions': True,
        })

        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.partner1.write({'parent_id': self.env['res.partner'].create({'name': 'Parent'}).id})

        # add customer account payment method to pos config
        self.pos_config.write({
            'payment_method_ids': [(4, self.customer_account_payment_method.id, 0)],
        })
        # change the currency of PoS config
        self.other_currency = self.setup_other_currency("EUR", rounding=0.001, rates=[(datetime.today().date(), 0.5)])
        self.pos_config.journal_id.write({
            'currency_id': self.other_currency.id
        })
        other_pricelist = self.env['product.pricelist'].create({
            'name': 'Public Pricelist Other',
            'currency_id': self.other_currency.id,
        })
        self.pos_config.write({
            'pricelist_id': other_pricelist.id,
            'available_pricelist_ids': [(6, 0, other_pricelist.ids)],
        })
        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # create pos order
        order = self.PosOrder.create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 6,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 6,
                'price_subtotal_incl': 6,
            })],
            'pricelist_id': self.pos_config.pricelist_id.id,
            'amount_paid': 6.0,
            'amount_total': 6.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })

        # pay for the order with customer account
        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': 2.0,
            'payment_method_id': self.cash_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': 4.0,
            'payment_method_id': self.customer_account_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        # close session
        current_session.action_pos_session_closing_control()

        accounting_partner = self.env['res.partner']._find_accounting_partner(self.partner1)
        self.assertEqual(accounting_partner.total_due, 8.0)

        # create invoice
        order.action_pos_order_invoice()
        self.assertEqual(accounting_partner.total_due, 8.0)

        # get journal entry that does the reverse payment, it the ref must contains Reversal
        reverse_payment = self.env['account.move'].search([('ref', 'ilike', "Reversal")])
        original_payment = self.env['account.move'].search([('ref', '=', current_session.display_name)])
        original_customer_payment_entry = original_payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        reverser_customer_payment_entry = reverse_payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        # check that both use the same account
        self.assertEqual(len(reverser_customer_payment_entry), 2)
        self.assertEqual(len(original_customer_payment_entry), 2)
        self.assertTrue(order.account_move.line_ids.partner_id == self.partner1.commercial_partner_id)
        self.assertEqual(reverser_customer_payment_entry[0].balance, -4.0)
        self.assertEqual(reverser_customer_payment_entry[1].balance, -8.0)
        self.assertEqual(reverser_customer_payment_entry[0].amount_currency, -2.0)
        self.assertEqual(reverser_customer_payment_entry[1].amount_currency, -4.0)
        self.assertEqual(original_customer_payment_entry.account_id.id, reverser_customer_payment_entry.account_id.id)
        self.assertEqual(reverser_customer_payment_entry.partner_id, original_customer_payment_entry.partner_id)

    def test_invoicing_after_closing_session_intermediary_account(self):
        """ Test that an invoice can be created after the session is closed """
        # create customer account payment method
        receivable_account = self.env.company.account_default_pos_receivable_account_id.copy()
        self.cash_payment_method.receivable_account_id = receivable_account

        self.product1 = self.env['product.product'].create({
            'name': 'Product A',
            'is_storable': True,
            'categ_id': self.env.ref('product.product_category_all').id,
        })
        self.partner1.write({'parent_id': self.env['res.partner'].create({'name': 'Parent'}).id})

        self.pos_config.open_ui()
        current_session = self.pos_config.current_session_id

        # create pos order
        order = self.PosOrder.create({
            'company_id': self.env.company.id,
            'session_id': current_session.id,
            'partner_id': self.partner1.id,
            'lines': [(0, 0, {
                'name': "OL/0001",
                'product_id': self.product1.id,
                'price_unit': 6,
                'discount': 0,
                'qty': 1,
                'tax_ids': [[6, False, []]],
                'price_subtotal': 6,
                'price_subtotal_incl': 6,
            })],
            'pricelist_id': self.pos_config.pricelist_id.id,
            'amount_paid': 6.0,
            'amount_total': 6.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
        })

        payment_context = {"active_ids": order.ids, "active_id": order.id}
        order_payment = self.PosMakePayment.with_context(**payment_context).create({
            'amount': 6.0,
            'payment_method_id': self.cash_payment_method.id
        })
        order_payment.with_context(**payment_context).check()

        # close session
        current_session.action_pos_session_closing_control()

        accounting_partner = self.env['res.partner']._find_accounting_partner(self.partner1)
        self.assertEqual(accounting_partner.total_due, 0.0)

        # create invoice
        order.action_pos_order_invoice()
        self.assertEqual(accounting_partner.total_due, 0.0)

        # get journal entry that does the reverse payment, it the ref must contains Reversal
        reverse_payment = self.env['account.move'].search([('ref', 'ilike', "Reversal")])
        original_payment = self.env['account.move'].search([('ref', '=', current_session.display_name)])
        original_customer_payment_entry = original_payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        reverser_customer_payment_entry = reverse_payment.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        # check that both use the same account
        self.assertEqual(original_customer_payment_entry.account_id, receivable_account)
        self.assertEqual(original_customer_payment_entry.account_id.id, reverser_customer_payment_entry.account_id.id)
        self.assertEqual(reverser_customer_payment_entry.partner_id, original_customer_payment_entry.partner_id)
        aml_receivable = self.env['account.move.line'].read_group([('account_type', '=', 'asset_receivable')], fields=['account_id'], groupby='matching_number')
        self.assertEqual(len(aml_receivable), 3)
        for aml_g in aml_receivable:
            self.assertEqual(aml_g['matching_number_count'], 2)

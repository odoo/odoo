# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBankRecWidget(TestBankRecWidgetCommon):

    def test_matching_sale_orders(self):
        self.partner_a.property_product_pricelist.currency_id = self.company_data['currency']

        so1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 2,
                'price_unit': 1000.0,
            })],
        })
        so2 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 2,
                'price_unit': 1000.0,
            })],
        })
        (so1 + so2).action_quotation_sent()

        st_line = self._create_st_line(amount=2300.0, payment_ref=f"turlututu {so1.name} tsoin {so2.name} tsoin")
        rule = self._create_reconcile_model()

        # Match directly the sale orders.
        self.assertDictEqual(
            rule._apply_rules(st_line, st_line._retrieve_partner()),
            {'sale_orders': so1 + so2, 'model': rule},
        )

        # Invoice one of them.
        so1.action_confirm()
        invoice = so1._create_invoices()
        invoice.action_post()
        invoice_line = invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        self.assertDictEqual(
            rule._apply_rules(st_line, st_line._retrieve_partner()),
            {'amls': invoice_line, 'model': rule},
        )

        # Fully reconcile the invoice.
        payment = self.env['account.payment.register']\
            .with_context(active_ids=invoice.ids, active_model='account.move')\
            .create({})\
            ._create_payments()
        aml = payment._seek_for_lines()[0]
        self.assertDictEqual(
            rule._apply_rules(st_line, st_line._retrieve_partner()),
            {'amls': aml, 'model': rule},
        )

    def test_partial_payment_matching_sale_orders(self):
        self.partner_a.property_product_pricelist.currency_id = self.company_data['currency']

        # Create a sale order for 2300
        so1 = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 2,
                'price_unit': 1000.0,
            })],
        })
        so1.action_quotation_sent()

        # Invoice
        so1.action_confirm()
        invoice = so1._create_invoices()
        invoice.action_post()

        # Partially pay the invoice for 1150
        payment = self.env['account.payment.register']\
            .with_context(active_ids=invoice.ids, active_model='account.move')\
            .create({'amount': 1150})\
            ._create_payments()
        payment_aml = payment._seek_for_lines()[0]

        # Statement line for the same amount
        st_line = self._create_st_line(amount=1150.0, payment_ref=f"turlututu {so1.name} tsoin tsoin")
        rule = self._create_reconcile_model()

        # Match the payment
        self.assertDictEqual(
            rule._apply_rules(st_line, st_line._retrieve_partner()),
            {'amls': payment_aml, 'model': rule},
        )

    def test_matching_sale_orders_with_legend(self):
        sequence = self.env['ir.sequence'].sudo().search(
            [('code', '=', 'sale.order'), ('company_id', 'in', (self.env.company.id, False))],
            order='company_id',
            limit=1,
        )
        sequence.prefix = 'SO/%(year)s/'

        so = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [Command.create({
                'product_id': self.product_a.id,
                'product_uom_qty': 2,
            })],
        })
        so.action_quotation_sent()

        st_line = self._create_st_line(amount=2300.0, payment_ref=so.name)
        rule = self._create_reconcile_model()

        # Match directly the sale orders.
        self.assertDictEqual(
            rule._apply_rules(st_line, st_line._retrieve_partner()),
            {'sale_orders': so, 'model': rule},
        )

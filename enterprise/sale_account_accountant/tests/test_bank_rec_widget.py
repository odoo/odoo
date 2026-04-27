# -*- coding: utf-8 -*-
from odoo import Command
from odoo.addons.account_accountant.tests.test_bank_rec_widget_common import TestBankRecWidgetCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestBankRecWidget(TestBankRecWidgetCommon):

    def create_order(self, **kwargs):
        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'product_uom_qty': 2,
                    'price_unit': 1000.0,
                })
            ],
            **kwargs,
        })
        order.action_quotation_sent()
        return order

    def test_matching_sale_orders(self):
        self.partner_a.property_product_pricelist.currency_id = self.company_data['currency']

        so1 = self.create_order(name='SO/2000/01')
        so2 = self.create_order(name='SO/2000/02')

        rule = self._create_reconcile_model()

        # Match directly the sale orders by the full name.
        st_line1 = self._create_st_line(amount=4000.0, payment_ref="turlututu SO/2000/01 tsoin SO/2000/02 tsoin")
        self.assertDictEqual(
            rule._apply_rules(st_line1, st_line1._retrieve_partner()),
            {'sale_orders': so1 + so2, 'model': rule},
        )

        st_line2 = self._create_st_line(amount=4000.0, payment_ref="turlututu SO200001 tsoin 200002 tsoin")
        self.assertDictEqual(
            rule._apply_rules(st_line2, st_line2._retrieve_partner()),
            {'sale_orders': so1, 'model': rule},
        )

        # Invoice one of them.
        so1.action_confirm()
        invoice = so1._create_invoices()
        invoice.action_post()
        invoice_line = invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        for st_line in st_line1 + st_line2:
            self.assertDictEqual(
                rule._apply_rules(st_line, st_line._retrieve_partner()),
                {'amls': invoice_line, 'model': rule},
            )

        # Partially pay the invoice.
        payment = self.env['account.payment.register']\
            .with_context(active_ids=invoice.ids, active_model='account.move')\
            .create({'amount': 100.0})\
            ._create_payments()
        payment_aml1 = payment._seek_for_lines()[0]
        for st_line in st_line1 + st_line2:
            self.assertDictEqual(
                rule._apply_rules(st_line, st_line._retrieve_partner()),
                {'amls': payment_aml1 + invoice_line, 'model': rule},
            )

        # Statement line that matches exactly the payment.
        st_line3 = self._create_st_line(amount=100.0, payment_ref="SO200001")
        self.assertDictEqual(
            rule._apply_rules(st_line3, st_line3._retrieve_partner()),
            {'amls': payment_aml1, 'model': rule},
        )

        # Fully pay the invoice.
        payment = self.env['account.payment.register']\
            .with_context(active_ids=invoice.ids, active_model='account.move')\
            .create({})\
            ._create_payments()
        payment_aml2 = payment._seek_for_lines()[0]
        for st_line in st_line1 + st_line2:
            self.assertDictEqual(
                rule._apply_rules(st_line, st_line._retrieve_partner()),
                {'amls': payment_aml1 + payment_aml2, 'model': rule},
            )

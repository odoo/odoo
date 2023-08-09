from odoo.fields import Command
from odoo.tests import tagged

from .common import TestSaleCommon


@tagged('post_install', '-at_install')
class TestSaleOrderCreditLimit(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.company.account_use_credit_limit = True

        buck_currency = cls.env['res.currency'].create({
            'name': 'TB',
            'symbol': 'TB',
        })
        cls.env['res.currency.rate'].create({
            'name': '2023-01-01',
            'rate': 2.0,
            'currency_id': buck_currency.id,
            'company_id': cls.env.company.id,
        })

        cls.buck_pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Buck Pricelist',
            'currency_id': buck_currency.id,
        })

    def test_warning_on_invoice_with_downpayment(self):
        # Activate the Credit Limit feature and set a value for partner_a.
        self.env.company.account_use_credit_limit = True
        self.partner_a.credit_limit = 1000.0

        # Create and confirm a SO to reach (but not exceed) partner_a's credit limit.
        sale_order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'name': self.company_data['product_order_no'].name,
                'product_id': self.company_data['product_order_no'].id,
                'product_uom_qty': 1,
                'product_uom': self.company_data['product_order_no'].uom_id.id,
                'price_unit': 1000.0,
                'tax_id': False,
            })]
        })

        # Check that partner_a's credit and credit_to_invoice is 0.0.
        self.assertEqual(self.partner_a.credit, 0.0)
        self.assertEqual(self.partner_a.credit_to_invoice, 0.0)

        # Make sure partner_a's credit_to_invoice includes the newly confirmed SO.
        sale_order.action_confirm()
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertEqual(self.partner_a.credit, 0.0)
        self.assertEqual(self.partner_a.credit_to_invoice, 1000.0)

        # Create a 50% down payment invoice.
        self.env['sale.advance.payment.inv'].with_context({
            'active_model': 'sale.order',
            'active_ids': [sale_order.id],
            'active_id': sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }).create({
            'advance_payment_method': 'percentage',
            'amount': 50,
            'deposit_account_id': self.company_data['default_account_revenue'].id,
        }).create_invoices()

        invoice = sale_order.invoice_ids

        # Check that the warning does not appear even though we are creating an invoice
        # that should bring partner_a's credit above its limit.
        self.assertEqual(invoice.partner_credit_warning, '')


        # Make the down payment invoice amount larger than the Amount to Invoice
        # and check that the warning appears with the correct amounts,
        # i.e. 1.500 instead of 2.500 (1.000 SO + 1.500 down payment invoice).
        invoice.invoice_line_ids.quantity = 3
        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa01,000.00\n"
            "Total amount due (including this document): $\xa01,500.00"
        )

        invoice.invoice_line_ids.quantity = 1
        invoice.action_post()

        # Create a credit note reversing the invoice
        self.env['account.move.reversal'].with_company(self.env.company).create(
            {
                'move_ids': [Command.set((invoice.id,))],
                'journal_id': invoice.journal_id.id
            }
        ).reverse_moves()

        credit_note = sale_order.invoice_ids[1]
        credit_note.action_post()

        # Check that the credit note is accounted for correctly for the amount_to_invoice
        self.assertEqual(sale_order.amount_to_invoice, sale_order.amount_total)

    def test_credit_limit_multicurrency(self):
        self.partner_a.credit_limit = 50

        order = self.env['sale.order'].create({
            'partner_id': self.partner_a.id,
            'pricelist_id': self.buck_pricelist.id,
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_order_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 45.0,
                    'tax_id': False,
                })
            ]
        })
        self.assertEqual(order.amount_total / order.currency_rate, 22.5)
        self.assertEqual(order.partner_credit_warning, '')

        order.write({
            'order_line': [
                Command.create({
                    'product_id': self.company_data['product_order_no'].id,
                    'product_uom_qty': 1,
                    'price_unit': 65.0,
                    'tax_id': False,
                })
            ],
        })
        self.assertEqual(order.amount_total / order.currency_rate, 55)
        self.assertEqual(
            order.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa050.00\n"
            "Total amount due (including this document): $\xa055.00"
        )

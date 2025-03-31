# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, tagged, users

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

        cls.company_data_2 = cls.setup_other_company()

        cls.sales_user = cls.company_data['default_user_salesman']
        cls.sales_user.write({
            'login': "notaccountman",
            'email': "bad@accounting.com",
        })

        cls.empty_order = cls.env['sale.order'].create({
            'partner_id': cls.partner_a.id,
        })

    def test_credit_limit_multi_company(self):
        # multi-company setup
        company2 = self.company_data_2['company']

        # Activate the Credit Limit feature
        company2.account_use_credit_limit = True

        # Create and confirm a SO for that company
        sale_order = company2.env['sale.order'].create({
            'company_id': company2.id,
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data_2['default_pricelist'].id,
            'order_line': [Command.create({
                'product_id': self.company_data_2['product_order_no'].id,
                'price_unit': 1000.0,
            })],
        })

        self.assertEqual(self.partner_a.with_company(company2).credit_to_invoice, 0.0)
        sale_order.action_confirm()

        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertEqual(self.partner_a.with_company(company2).credit_to_invoice, 1000.0)
        partner_a_multi_company = self.partner_a.with_context(allowed_company_ids=[self.env.company.id, company2.id])
        self.assertEqual(partner_a_multi_company.credit_to_invoice, 0.0)
        self.assertEqual(self.partner_a.credit_to_invoice, 0.0)

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
        self.env['account.move.reversal'].with_company(self.env.company).with_context(
            active_model="account.move",
            active_ids=invoice.ids,
        ).create({
            'journal_id': invoice.journal_id.id,
        }).reverse_moves()

        credit_note = sale_order.invoice_ids[1]
        credit_note.action_post()

        # Check that the credit note is accounted for correctly for the amount_to_invoice
        self.assertEqual(sale_order.amount_to_invoice, sale_order.amount_total)

    def test_credit_limit_multicurrency(self):
        self.partner_a.credit_limit = 50

        self.assertRecordValues(self.partner_a, [{
            'credit': 0.0,
            'credit_to_invoice': 0.0,
        }])

        order = self.empty_order
        order.write({
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

        # Make sure partner_a's credit_to_invoice includes the newly confirmed SO in the correct currency
        order.action_confirm()
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertRecordValues(self.partner_a, [{
            'credit': 0.0,
            'credit_to_invoice': 55.0,
        }])

        # Make sure the invoice amount is converted correctly for the warning
        invoice = order._create_invoices(final=True)
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa050.00\n"
            "Total amount due (including this document): $\xa055.00"
        )

        # Make sure the invoice amount is converted correctly for the partner.credit computation
        invoice.action_post()
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertRecordValues(self.partner_a, [{
            'credit': 55.0,
            'credit_to_invoice': 0.0,
        }])

    def test_invoice_independent_of_credit_to_invoice(self):
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
                'product_id': self.company_data['product_order_no'].id,
                'price_unit': 1000.0,
            })]
        })

        # Check that partner_a's credit and credit_to_invoice is 0.0.
        self.assertRecordValues(self.partner_a, [{
            'credit': 0.0,
            'credit_to_invoice': 0.0,
        }])

        # Make sure partner_a's credit_to_invoice includes the newly confirmed SO.
        sale_order.action_confirm()
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertRecordValues(self.partner_a, [{
            'credit': 0.0,
            'credit_to_invoice': 1000.0,
        }])

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_line_ids': [(0, 0, {
                'name': 'test line',
                'quantity': 1,
                'price_unit': 100.0,  # <= 1000 (sales order amount_total)
                'tax_ids': False,
            })],
        })
        self.assertRecordValues(self.partner_a, [{
            'credit': 0.0,
            'credit_to_invoice': 1000.0,
        }])

        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa01,000.00\n"
            "Total amount due (including sales orders and this document): $\xa01,100.00"
        )

        invoice.invoice_line_ids[0].price_unit = 2000  # > 1000 (sales order amount_total)
        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa01,000.00\n"
            "Total amount due (including sales orders and this document): $\xa03,000.00"
        )

        invoice.action_post()
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertRecordValues(self.partner_a, [{
            'credit': 2000.0,
            'credit_to_invoice': 1000.0,
        }])

    def test_credit_limit_and_warning_overinvoiced_sales_order(self):
        # Activate the Credit Limit feature and set a value for partner_a.
        self.env.company.account_use_credit_limit = True
        self.partner_a.credit_limit = 1000.0

        # Create 2 SOs
        sale_order_values = {
            'partner_id': self.partner_a.id,
            'partner_invoice_id': self.partner_a.id,
            'partner_shipping_id': self.partner_a.id,
            'pricelist_id': self.company_data['default_pricelist'].id,
            'order_line': [Command.create({
                'product_id': self.company_data['product_order_no'].id,
                'price_unit': 1000.0,
            })]
        }
        sale_orders = self.env['sale.order'].create(
            [sale_order_values] * 2
        )

        # Check that partner_a's credit and credit_to_invoice is 0.0.
        self.assertRecordValues(self.partner_a, [{
            'credit': 0.0,
            'credit_to_invoice': 0.0,
        }])

        for order in sale_orders:
            order.action_confirm()

        # Make sure partner_a's credit_to_invoice includes the newly confirmed SOs.
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertRecordValues(self.partner_a, [{
            'credit': 0.0,
            'credit_to_invoice': 2000.0,
        }])

        # Invoice 1 of the SOs.
        sale_order = sale_orders[0]
        self.assertEqual(sale_order.amount_to_invoice, 1000.0)
        invoice = sale_order._create_invoices(final=True)
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertEqual(invoice.amount_total, 1000.0)
        # Modify the amount of the invoice to be greater than the amount of the (single) SO.
        invoice.invoice_line_ids[0].price_unit = 2000.0

        # Confirming the invoice will reduce the credit_to_invoice by 1000.
        # This is since the amount of the sales order it originates from is 1000 and
        # the amount of the invoice is more than 1000.
        self.assertEqual(
            invoice.partner_credit_warning,
            "partner_a has reached its credit limit of: $\xa01,000.00\n"
            "Total amount due (including sales orders and this document): $\xa03,000.00"
        )

        # Check that confirming the invoice changes the credit amounts as described above.
        invoice.action_post()
        self.partner_a.invalidate_recordset(['credit', 'credit_to_invoice'])
        self.assertRecordValues(self.partner_a, [{
            'credit': 2000.0,
            'credit_to_invoice': 1000.0,
        }])

    @users('notaccountman')
    def test_credit_limit_access(self):
        """Ensure credit warning gets displayed without Accounting access."""
        self.empty_order.sudo().user_id = self.env.user
        self.empty_order.sudo().partner_id.credit_limit = self.product_a.list_price

        for group in self.partner_a._fields['credit'].groups.split(','):
            self.assertFalse(self.env.user.has_group(group))

        with Form(self.empty_order.with_env(self.env)) as order_form:
            with order_form.order_line.new() as sol:
                sol.product_id = self.product_a
                sol.tax_id.clear()
            self.assertFalse(
                order_form.partner_credit_warning,
                "No credit warning should be displayed (yet)",
            )
            with order_form.order_line.edit(0) as sol:
                sol.tax_id.add(self.tax_sale_a)
            self.assertTrue(
                order_form.partner_credit_warning,
                "Credit warning should be displayed",
            )

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields
from odoo.exceptions import UserError
from odoo.fields import Command
from odoo.tests import freeze_time, tagged

from odoo.addons.sale.tests.common import TestSaleCommon


@freeze_time('2022-01-01')
@tagged('post_install', '-at_install')
class TestAccruedSaleOrders(TestSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency = cls.setup_other_currency('EUR')
        cls.alt_inc_account = cls.company_data['default_account_revenue'].copy()
        # set 'invoice_policy' to 'delivery' to take 'qty_delivered' into account when computing 'untaxed_amount_to_invoice'
        # set 'type' to 'service' to allow manualy set 'qty_delivered' even with sale_stock installed
        cls.product_a.update({
            'type': 'service',
            'invoice_policy': 'delivery',
        })
        cls.product_b.update({
            'type': 'service',
            'invoice_policy': 'delivery',
            'property_account_income_id': cls.alt_inc_account.id,
        })
        cls.default_plan = cls.env['account.analytic.plan'].create({'name': 'Default'})
        cls.analytic_account_a = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_a',
            'plan_id': cls.default_plan.id,
            'company_id': False,
        })
        cls.analytic_account_b = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_b',
            'plan_id': cls.default_plan.id,
            'company_id': False,
        })
        cls.sale_order = cls.env['sale.order'].with_context(tracking_disable=True).create({
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({
                    'name': cls.product_a.name,
                    'product_id': cls.product_a.id,
                    'product_uom_qty': 10.0,
                    'price_unit': cls.product_a.list_price,
                    'tax_ids': False,
                    'analytic_distribution': {
                        cls.analytic_account_a.id : 80.0,
                        cls.analytic_account_b.id : 20.0,
                    },
                }),
                Command.create({
                    'name': cls.product_b.name,
                    'product_id': cls.product_b.id,
                    'product_uom_qty': 10.0,
                    'price_unit': cls.product_b.list_price,
                    'tax_ids': False,
                    'analytic_distribution': {
                        cls.analytic_account_b.id : 100.0,
                    },
                })
            ]
        })
        cls.sale_order.action_confirm()
        cls.account_expense = cls.company_data['default_account_expense']
        cls.account_revenue = cls.company_data['default_account_revenue']
        cls.wizard = cls.env['account.accrued.orders.wizard'].with_context({
            'active_model': 'sale.order',
            'active_ids': cls.sale_order.ids,
        }).create({
            'account_id': cls.account_expense.id,
            'date': fields.Date.today(),
        })

    def test_accrued_order(self):
        # self.wizard = self.wizard.with_context(accrual_entry_date=fields.Date.today())
        self.wizard.date = fields.Date.today()
        # nothing to invoice : no entries to be created
        with self.assertRaises(UserError):
            self.wizard.create_entries()

        # 5 qty of each product invoiceable
        self.sale_order.order_line.qty_delivered = 5
        # Call accrual wizard at today date because calling in the past will
        # re-compute delivred and invoiced quantities for this date and thus
        # generate nothing since there was no delivered quantity at this time.
        account_move = self.env['account.move'].search(self.wizard.create_entries()['domain'])
        self.assertRecordValues(account_move.line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 5000, 'credit': 0},
            {'account_id': self.alt_inc_account.id, 'debit': 1000, 'credit': 0},
            {'account_id': self.wizard.account_id.id, 'debit': 0, 'credit': 6000},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 5000},
            {'account_id': self.alt_inc_account.id, 'debit': 0, 'credit': 1000},
            {'account_id': self.wizard.account_id.id, 'debit': 6000, 'credit': 0},
        ])

        # delivered products invoiced, nothing to invoice left
        invoices = self.sale_order._create_invoices()
        invoices.action_post()
        with self.assertRaises(UserError):
            self.wizard.create_entries()
        self.assertTrue(self.wizard.display_amount)

    def test_multi_currency_accrued_order(self):
        # 5 qty of each product billeable
        self.sale_order.order_line.qty_delivered = 5
        # self.sale_order.order_line.product_uom_qty = 5
        # set currency != company currency
        self.sale_order.currency_id = self.other_currency
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 5000 / 2, 'credit': 0, 'amount_currency': 5000},
            {'account_id': self.alt_inc_account.id, 'debit': 1000 / 2, 'credit': 0, 'amount_currency': 1000},
            {'account_id': self.account_expense.id, 'debit': 0, 'credit': 6000 / 2, 'amount_currency': 0.0},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 5000 / 2, 'amount_currency': -5000},
            {'account_id': self.alt_inc_account.id, 'debit': 0, 'credit': 1000 / 2, 'amount_currency': -1000},
            {'account_id': self.account_expense.id, 'debit': 6000 / 2, 'credit': 0, 'amount_currency': 0.0},
        ])

    def test_analytic_account_accrued_order(self):
        self.sale_order.order_line.qty_delivered = 10

        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 10000.0, 'credit': 0.0, 'analytic_distribution': {str(self.analytic_account_a.id): 80.0, str(self.analytic_account_b.id): 20.0}},
            {'account_id': self.alt_inc_account.id, 'debit': 2000.0, 'credit': 0.0, 'analytic_distribution': {str(self.analytic_account_b.id): 100.0}},
            {'account_id': self.account_expense.id, 'debit': 0.0, 'credit': 12000.0, 'analytic_distribution': {str(self.analytic_account_a.id): 66.67, str(self.analytic_account_b.id): 33.33}},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0.0, 'credit': 10000.0, 'analytic_distribution': {str(self.analytic_account_a.id): 80.0, str(self.analytic_account_b.id): 20.0}},
            {'account_id': self.alt_inc_account.id, 'debit': 0.0, 'credit': 2000.0, 'analytic_distribution': {str(self.analytic_account_b.id): 100.0}},
            {'account_id': self.account_expense.id, 'debit': 12000.0, 'credit': 0.0, 'analytic_distribution': {str(self.analytic_account_a.id): 66.67, str(self.analytic_account_b.id): 33.33}},

        ])

    def test_product_name_in_accrued_revenue_entry(self):
        self.sale_order.order_line.qty_delivered = 5

        so_context = {
            'active_model': 'sale.order',
            'active_ids': self.sale_order.ids,
            'active_id': self.sale_order.id,
            'default_journal_id': self.company_data['default_journal_sale'].id,
        }
        payment_params = {
            'advance_payment_method': 'percentage',
            'amount': 50.0,
        }
        downpayment = self.env['sale.advance.payment.inv'].with_context(so_context).create(payment_params)
        invoice = downpayment._create_invoices(self.sale_order)
        invoice.invoice_date = self.wizard.date
        invoice.action_post()
        self.wizard.create_entries()
        self.assertFalse(self.wizard.display_amount)
        self.assertRecordValues(self.env['account.move'].search(self.wizard.create_entries()['domain']).line_ids, [
            # reverse move lines
            {'account_id': self.account_revenue.id, 'debit': 5000, 'credit': 0},
            {'account_id': self.alt_inc_account.id, 'debit': 1000, 'credit': 0},
            {'account_id': self.wizard.account_id.id, 'debit': 0, 'credit': 6000},
            # move lines
            {'account_id': self.account_revenue.id, 'debit': 0, 'credit': 5000},
            {'account_id': self.alt_inc_account.id, 'debit': 0, 'credit': 1000},
            {'account_id': self.wizard.account_id.id, 'debit': 6000, 'credit': 0},
        ])

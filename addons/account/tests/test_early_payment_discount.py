# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestAccountEarlyPaymentDiscount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Payment Terms
        cls.early_pay_10_percents_10_days = cls.env['account.payment.term'].create({
            'name': '10% discount if paid within 10 days',
            'company_id': cls.company_data['company'].id,
            'line_ids': [Command.create({
                'value': 'balance',
                'days': 0,
                'discount_percentage': 10,
                'discount_days': 10
            })]
        })

        cls.early_pay_mixed_5_10 = cls.env['account.payment.term'].create({
            'name': '5 percent discount on 50% of the amount, 10% on the balance, if payed within 10 days',
            'company_id': cls.company_data['company'].id,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 50,
                    'days': 30,
                    'discount_percentage': 5,
                    'discount_days': 10
                }),
                Command.create({
                    'value': 'balance',
                    'days': 30,
                    'discount_percentage': 10,
                    'discount_days': 10
                })],
        })

    # ========================== Tests Payment Terms ==========================
    def test_early_payment_end_date(self):
        inv_1200_10_percents_discount_no_tax = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'line', 'price_unit': 1200.0, 'tax_ids': []
            })],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        for line in inv_1200_10_percents_discount_no_tax.line_ids:
            if line.display_type == 'payment_term':
                self.assertEqual(
                    line.discount_date,
                    fields.Date.from_string('2019-01-11') or False
                )

    # ========================== Tests Payment Register ==========================
    def test_register_discounted_payment_on_single_invoice(self):
        self.company_data['company'].early_pay_discount_computation = 'included'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_1.action_post()
        active_ids = out_invoice_1.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2017-01-01',
        })._create_payments()

        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -1000.0},
            {
                'account_id': self.env.company['account_journal_early_pay_discount_loss_account_id'].id,
                'amount_currency': 100.0,
            },
            {'amount_currency': 900.0},
        ])

    def test_register_discounted_payment_on_single_invoice_with_tax(self):
        self.company_data['company'].early_pay_discount_computation = 'included'
        inv_1500_10_percents_discount_tax_incl_15_percents_tax = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({'name': 'line', 'price_unit': 1500.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        inv_1500_10_percents_discount_tax_incl_15_percents_tax.action_post()
        active_ids = inv_1500_10_percents_discount_tax_incl_15_percents_tax.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2017-01-01',
        })._create_payments()

        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -1552.5},
            {'amount_currency': -150.0},
            {'amount_currency': -22.5},
            {'amount_currency': 1725.0},
        ])

    def test_register_discounted_payment_multi_line_discount(self):
        self.company_data['company'].early_pay_discount_computation = 'included'
        inv_mixed_lines_discount_and_no_discount = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({'name': 'line', 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]}),
                Command.create({'name': 'line', 'price_unit': 2000.0, 'tax_ids': None})
            ],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        inv_mixed_lines_discount_and_no_discount.action_post()
        active_ids = inv_mixed_lines_discount_and_no_discount.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2017-01-01',
            'group_payment': True
        })._create_payments()

        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -2835.0},
            {'amount_currency': -200.0},
            {'amount_currency': -100.0},
            {'amount_currency': -15.0},
            {'amount_currency': 3150.0},
        ])

    def test_register_discounted_payment_multi_line_multi_discount(self):
        self.company_data['company'].early_pay_discount_computation = 'included'
        inv_mixed_lines_multi_discount = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({'name': 'line', 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]}),
                Command.create({'name': 'line', 'price_unit': 2000.0, 'tax_ids': None})
            ],
            'invoice_payment_term_id': self.early_pay_mixed_5_10.id,
        })
        inv_mixed_lines_multi_discount.action_post()
        active_ids = inv_mixed_lines_multi_discount.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move',
                                                                     active_ids=active_ids).create({
            'payment_date': '2019-01-01',
            'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -2913.75},
            {'amount_currency': -150.0},
            {'amount_currency': -75},
            {'amount_currency': -11.25},
            {'amount_currency': 3150.0},
        ])

    def test_register_discounted_payment_multi_line_multi_discount_tax_excluded(self):
        self.company_data['company'].early_pay_discount_computation = 'excluded'
        inv_mixed_lines_multi_discount = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({'name': 'line', 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]}),
                Command.create({'name': 'line', 'price_unit': 2000.0, 'tax_ids': None})
            ],
            'invoice_payment_term_id': self.early_pay_mixed_5_10.id,
        })
        inv_mixed_lines_multi_discount.action_post()
        active_ids = inv_mixed_lines_multi_discount.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move',
                                                                     active_ids=active_ids).create({
            'payment_date': '2019-01-01',
            'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -2925.00},
            {'amount_currency': -225},
            {'amount_currency': 3150.0},
        ])

    def test_register_discounted_payment_multi_line_multi_discount_tax_mixed(self):
        self.env.company.early_pay_discount_computation = 'mixed'
        inv_mixed_lines_multi_discount = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({'name': 'line', 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]}),
                Command.create({'name': 'line', 'price_unit': 2000.0, 'tax_ids': None})
            ],
            'invoice_payment_term_id': self.early_pay_mixed_5_10.id,
        })
        inv_mixed_lines_multi_discount.action_post()
        active_ids = inv_mixed_lines_multi_discount.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -2902.50},
            {'amount_currency': -225.0},
            {'amount_currency': 3127.50},
        ])

    def test_register_discounted_payment_multi_line_multi_discount_tax_mixed_too_late(self):
        self.env.company.early_pay_discount_computation = 'mixed'
        inv_mixed_lines_multi_discount = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({'name': 'line', 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]}),
                Command.create({'name': 'line', 'price_unit': 2000.0, 'tax_ids': None})
            ],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        inv_mixed_lines_multi_discount.action_post()
        active_ids = inv_mixed_lines_multi_discount.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-31', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -3135.00},
            {'amount_currency': 3135.00},
        ])

    def test_register_payment_batch_included(self):
        self.env.company.early_pay_discount_computation = 'included'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -3000.0},
            {'amount_currency': 300.0},
            {'amount_currency': 2700},
        ])

    def test_register_payment_batch_excluded(self):
        self.env.company.early_pay_discount_computation = 'excluded'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -3150.0},
            {'amount_currency': 300.0},
            {'amount_currency': 2850},
        ])

    def test_register_payment_batch_mixed(self):
        self.env.company.early_pay_discount_computation = 'mixed'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -3135.0},
            {'amount_currency': 300.0},
            {'amount_currency': 2835.0},
        ])

    def test_register_payment_batch_mixed_one_too_late(self):
        self.env.company.early_pay_discount_computation = 'mixed'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -3135.0},
            {'amount_currency': 200.0},
            {'amount_currency': 2935.0},

        ])

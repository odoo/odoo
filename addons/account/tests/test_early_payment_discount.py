# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged, Form
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestAccountEarlyPaymentDiscount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR')
        # Payment Terms
        cls.early_pay_10_percents_10_days = cls.env['account.payment.term'].create({
            'name': '10% discount if paid within 10 days',
            'company_id': cls.company_data['company'].id,
            'early_discount': True,
            'discount_percentage': 10,
            'discount_days': 10,
            'line_ids': [Command.create({
                'value': 'percent',
                'nb_days': 0,
                'value_amount': 100,
            })]
        })

        cls.pay_term_net_30_days = cls.env['account.payment.term'].create({
            'name': 'Net 30 days',
            'line_ids': [
                (0, 0, {
                    'value_amount': 100,
                    'value': 'percent',
                    'nb_days': 30,
                }),
            ],
        })

        cls.pay_30_percents_now_balance_60_days = cls.env['account.payment.term'].create({
            'name': '30% Now, Balance 60 Days',
            'line_ids': [
                Command.create({
                    'value_amount': 30,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 70,
                    'value': 'percent',
                    'nb_days': 60,
                })
            ]
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

    def test_early_payment_date_eligibility(self):
        """
        Test to check early payment eligibility is based on the date stored
        on the payment term line
        """
        inv = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'line', 'price_unit': 1200.0, 'tax_ids': []
            })],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        inv.action_post()
        self.assertTrue(inv._is_eligible_for_early_payment_discount(inv.currency_id, fields.Date.from_string('2019-01-10')))
        self.assertFalse(inv._is_eligible_for_early_payment_discount(inv.currency_id, fields.Date.from_string('2019-01-12')))
        # Changing number of days on payment term should not change the discount eligibility
        self.early_pay_10_percents_10_days.discount_days = 5
        self.assertTrue(inv._is_eligible_for_early_payment_discount(inv.currency_id, fields.Date.from_string('2019-01-10')))
        self.assertFalse(inv._is_eligible_for_early_payment_discount(inv.currency_id, fields.Date.from_string('2019-01-12')))

    def test_early_payment_date_eligibility2(self):
        self.early_pay_10_percents_10_days.early_discount = False
        inv = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'line', 'price_unit': 1200.0, 'tax_ids': []
            })],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        inv.action_post()
        self.assertFalse(inv._is_eligible_for_early_payment_discount(inv.currency_id, fields.Date.from_string('2019-01-10')))
        self.assertFalse(inv._is_eligible_for_early_payment_discount(inv.currency_id, fields.Date.from_string('2019-01-12')))

        # Activate the early discount after the invoice has been posted.
        # Calling _is_eligible_for_early_payment_discount shouldn't fail
        self.early_pay_10_percents_10_days.early_discount = True
        self.assertFalse(inv._is_eligible_for_early_payment_discount(inv.currency_id, fields.Date.from_string('2019-01-10')))
        self.assertFalse(inv._is_eligible_for_early_payment_discount(inv.currency_id, fields.Date.from_string('2019-01-12')))

    def test_invoice_report_without_invoice_date(self):
        """
        Ensure that an invoice with an early discount payment term
        and no invoice date can be previewed or printed.
        """
        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
            'invoice_line_ids': [Command.create({
                'name': 'line1',
            })]
        }])

        # Assert that the invoice date is not set
        self.assertEqual(out_invoice.invoice_date, False)

        with self.allow_pdf_render():
            report = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('account.account_invoices', res_ids=out_invoice.id)
        self.assertTrue(report)

        #Test for invoices with multiple due dates and no early discount
        out_invoice.invoice_payment_term_id = self.pay_30_percents_now_balance_60_days
        with self.allow_pdf_render():
            new_report = self.env['ir.actions.report']._render_qweb_pdf('account.account_invoices', res_ids=out_invoice.id)
        self.assertTrue(new_report)

    # ========================== Tests Taxes Amounts =============================
    def test_fixed_tax_amount_discounted_payment_mixed(self):
        fixed_tax = self.env['account.tax'].create({
            'name': 'Test 0.05',
            'amount_type': 'fixed',
            'amount': 0.05,
        })
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'mixed'
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'price_unit': 1000.0,
                'tax_ids': [Command.set(self.product_a.taxes_id.ids + fixed_tax.ids)], #15% tax + fixed 0.05
            })],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        self.assertInvoiceValues(invoice, [
            # pylint: disable=bad-whitespace
            {'display_type': 'epd',             'balance': -100.0},
            {'display_type': 'epd',             'balance': 100.0},
            {'display_type': 'product',         'balance': -1000.0},
            {'display_type': 'tax',             'balance': -135},
            {'display_type': 'tax',             'balance': -0.05},
            {'display_type': 'payment_term',    'balance': 1135.05},
        ], {
            'amount_untaxed': 1000.0,
            'amount_tax': 135.05,
            'amount_total': 1135.05,
         })

    # ========================== Tests Payment Register ==========================
    def test_register_discounted_payment_on_single_invoice(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'included'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_1.action_post()
        active_ids = out_invoice_1.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-02',
        })._create_payments()

        self.assertTrue(payments.is_reconciled)
        self.assertEqual(
            payments.move_id.line_ids.sorted('balance').mapped('amount_currency'),
            [-1000.0, 100.0, 900.0],
        )

    def test_register_discounted_payment_on_single_invoice_with_fixed_tax_1(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'included'
        fixed_tax = self.env['account.tax'].create({
            'name': 'Test 0.05',
            'amount_type': 'fixed',
            'amount': 0.05,
            'type_tax_use': 'purchase',
        })

        inv = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'price_unit': 1500.0,
                'tax_ids': [Command.set(self.product_a.supplier_taxes_id.ids + fixed_tax.ids)]
            })],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        inv.action_post()
        active_ids = inv.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2017-01-01',
        })._create_payments()

        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -1552.55},
            {'amount_currency': -150.0},
            {'amount_currency': -22.5},
            {'amount_currency': 1725.05},
        ])

    def test_register_discounted_payment_on_single_invoice_with_fixed_tax_2(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'included'
        fixed_tax = self.env['account.tax'].create({
            'name': 'Test 0.05',
            'amount_type': 'fixed',
            'amount': 0.05,
            'type_tax_use': 'purchase',
        })

        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({
                'name': 'line',
                'price_unit': 50.0,
                'tax_ids': [Command.set(self.product_a.supplier_taxes_id.ids + fixed_tax.ids)]
            })],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        invoice.action_post()
        payments = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'payment_date': '2017-01-01'})\
            ._create_payments()

        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -51.80},
            {'amount_currency': -5.00},
            {'amount_currency': -0.75},
            {'amount_currency': 57.55},
        ])

    def test_register_discounted_payment_on_single_invoice_with_tax(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'included'
        inv_1500_10_percents_discount_tax_incl_15_percents_tax = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [Command.create({'name': 'line', 'price_unit': 1500.0, 'tax_ids': [Command.set(self.product_a.supplier_taxes_id.ids)]})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        inv_1500_10_percents_discount_tax_incl_15_percents_tax.action_post()
        active_ids = inv_1500_10_percents_discount_tax_incl_15_percents_tax.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2017-01-01',
        })._create_payments()

        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -1552.5},
            {'amount_currency': -150.0},
            {'amount_currency': -22.5},
            {'amount_currency': 1725.0},
        ])

    def test_register_discounted_payment_on_single_out_invoice_with_tax(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'included'
        inv_1500_10_percents_discount_tax_incl_15_percents_tax = self.env['account.move'].create({
            'move_type': 'out_invoice',
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
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -1725.0},
            {'amount_currency': 22.5},
            {'amount_currency': 150.0},
            {'amount_currency': 1552.5},
        ])

    def test_register_discounted_payment_multi_line_discount(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'included'
        inv_mixed_lines_discount_and_no_discount = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({'name': 'line', 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.supplier_taxes_id.ids)]}),
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
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -2835.0},
            {'amount_currency': -200.0},
            {'amount_currency': -100.0},
            {'amount_currency': -15.0},
            {'amount_currency': 3150.0},
        ])

    def test_register_payment_batch_included(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'included'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -3000.0},
            {'amount_currency': 300.0},
            {'amount_currency': 2700},
        ])

    def test_register_payment_batch_excluded(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'excluded'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -3150.0},
            {'amount_currency': 300.0},
            {'amount_currency': 2850},
        ])

    def test_register_payment_batch_mixed(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'mixed'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -3135.0},
            {'amount_currency': 300.0},
            {'amount_currency': 2835.0},
        ])

    def test_register_payment_batch_mixed_one_too_late(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'mixed'
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })

        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': True
        })._create_payments()
        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -3135.0},
            {'amount_currency': 200.0},
            {'amount_currency': 2935.0},
        ])

    def test_mixed_epd_with_draft_invoice(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'mixed'
        tax = self.env['account.tax'].create({
            'name': 'WonderTax',
            'amount': 10,
        })
        with Form(self.env['account.move'].with_context(default_move_type='out_invoice')) as invoice:
            invoice.partner_id = self.partner_a
            invoice.invoice_date = fields.Date.from_string('2022-02-21')
            invoice.invoice_payment_term_id = self.early_pay_10_percents_10_days
            with invoice.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_a
                line_form.price_unit = 1000
                line_form.quantity = 1
                line_form.tax_ids.clear()
                line_form.tax_ids.add(tax)
            self._assert_tax_totals_summary(invoice.tax_totals, {
                'same_tax_base': False,
                'currency_id': self.env.company.currency_id.id,
                'base_amount_currency': 1000.0,
                'tax_amount_currency': 90.0,
                'total_amount_currency': 1090.0,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 1000.0,
                        'tax_amount_currency': 90.0,
                        'tax_groups': [
                            {
                                'id': tax.tax_group_id.id,
                                'base_amount_currency': 900.0,
                                'tax_amount_currency': 90.0,
                                'display_base_amount_currency': 900.0,
                            },
                        ],
                    },
                ],
            })

    def test_intracomm_bill_with_early_payment_included(self):
        tax_tags = self.env['account.account.tag'].create([{
            'name': f'tax_tag_{i}',
            'applicability': 'taxes',
            'country_id': self.env.company.account_fiscal_country_id.id,
        } for i in range(6)])

        intracomm_tax = self.env['account.tax'].create({
            'name': 'tax20',
            'amount_type': 'percent',
            'amount': 20,
            'type_tax_use': 'purchase',
            'invoice_repartition_line_ids': [
                # pylint: disable=bad-whitespace
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0,    'tag_ids': [Command.set(tax_tags[0].ids)]}),
                Command.create({'repartition_type': 'tax',  'factor_percent': 100.0,    'tag_ids': [Command.set(tax_tags[1].ids)]}),
                Command.create({'repartition_type': 'tax',  'factor_percent': -100.0,   'tag_ids': [Command.set(tax_tags[2].ids)]}),
            ],
            'refund_repartition_line_ids': [
                # pylint: disable=bad-whitespace
                Command.create({'repartition_type': 'base', 'factor_percent': 100.0,    'tag_ids': [Command.set(tax_tags[3].ids)]}),
                Command.create({'repartition_type': 'tax',  'factor_percent': 100.0,    'tag_ids': [Command.set(tax_tags[4].ids)]}),
                Command.create({'repartition_type': 'tax',  'factor_percent': -100.0,   'tag_ids': [Command.set(tax_tags[5].ids)]}),
            ],
        })

        early_payment_term = self.env['account.payment.term'].create({
            'name': "early_payment_term",
            'company_id': self.company_data['company'].id,
            'early_pay_discount_computation': 'included',
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 7,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100.0,
                    'nb_days': 30,
                }),
            ],
        })

        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': early_payment_term.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': 'line',
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(intracomm_tax.ids)],
                }),
            ],
        })
        bill.action_post()

        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=bill.ids)\
            .create({'payment_date': '2019-01-01'})\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('balance'), [
            # pylint: disable=bad-whitespace
            {'amount_currency': -980.0, 'tax_ids': [],                  'tax_tag_ids': []},
            {'amount_currency': -20.0,  'tax_ids': intracomm_tax.ids,   'tax_tag_ids': tax_tags[3].ids},
            {'amount_currency': -4.0,   'tax_ids': [],                  'tax_tag_ids': tax_tags[4].ids},
            {'amount_currency': 4.0,    'tax_ids': [],                  'tax_tag_ids': tax_tags[5].ids},
            {'amount_currency': 1000.0, 'tax_ids': [],                  'tax_tag_ids': []},
        ])

    def test_mixed_early_discount_with_tag_on_tax_base_line(self):
        """
        Ensure that early payment discount line grouping works properly when
        using a tax that adds tax tags to its base line.
        """
        tax_tag = self.env['account.account.tag'].create({
            'name': 'tax_tag',
            'applicability': 'taxes',
            'country_id': self.env.company.account_fiscal_country_id.id,
        })

        tax_21 = self.env['account.tax'].create({
            'name': "tax_21",
            'amount': 21,
            'invoice_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100,
                    'repartition_type': 'base',
                    'tag_ids': [Command.set(tax_tag.ids)],
                }),
                Command.create({
                    'factor_percent': 100, 'repartition_type': 'tax',
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'factor_percent': 100, 'repartition_type': 'base',
                }),
                Command.create({
                    'factor_percent': 100, 'repartition_type': 'tax',
                }),
            ],
        })

        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'mixed'
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        bill.write({
            'invoice_line_ids': [
                Command.create({
                    'name': 'line1',
                    'price_unit': 1000.0,
                    'tax_ids': [Command.set(tax_21.ids)],
                }),
            ],
        })
        bill.write({
            'invoice_line_ids': [Command.create({
                'name': 'line2',
                'price_unit': 1000.0,
                'tax_ids': [Command.set(tax_21.ids)],
            })],
        })
        epd_lines = bill.line_ids.filtered(lambda line: line.display_type == 'epd')
        self.assertRecordValues(epd_lines.sorted('balance'), [
            {'balance': -200.0},
            {'balance': 200.0},
        ])

    def test_mixed_epd_with_tax_included(self):
        early_pay_2_percents_10_days = self.env['account.payment.term'].create({
            'name': '2% discount if paid within 10 days',
            'company_id': self.company_data['company'].id,
            'early_discount': True,
            'discount_percentage': 2,
            'discount_days': 10,
            'early_pay_discount_computation': 'mixed',
            'line_ids': [Command.create({
                'value': 'percent',
                'nb_days': 0,
                'value_amount': 100,
            })]
        })
        tax = self.env['account.tax'].create({
            'name': 'Tax 21% included',
            'amount': 21,
            'price_include_override': 'tax_included',
        })

        with Form(self.env['account.move'].with_context(default_move_type='out_invoice')) as invoice:
            invoice.partner_id = self.partner_a
            invoice.invoice_date = fields.Date.from_string('2022-02-21')
            invoice.invoice_payment_term_id = early_pay_2_percents_10_days
            with invoice.invoice_line_ids.new() as line_form:
                line_form.product_id = self.product_a
                line_form.price_unit = 121
                line_form.quantity = 1
                line_form.tax_ids.clear()
                line_form.tax_ids.add(tax)
            self._assert_tax_totals_summary(invoice.tax_totals, {
                'same_tax_base': False,
                'currency_id': self.env.company.currency_id.id,
                'base_amount_currency': 100.0,
                'tax_amount_currency': 20.58,
                'total_amount_currency': 120.58,
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'base_amount_currency': 100.0,
                        'tax_amount_currency': 20.58,
                        'tax_groups': [
                            {
                                'id': tax.tax_group_id.id,
                                'base_amount_currency': 98.0,
                                'tax_amount_currency': 20.58,
                                'display_base_amount_currency': 98.0,
                            },
                        ],
                    },
                ],
            })

    def test_mixed_epd_with_tax_no_duplication(self):
        (self.pay_terms_a | self.early_pay_10_percents_10_days).write({'early_pay_discount_computation': 'mixed'})
        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({'name': 'line', 'price_unit': 100.0, 'tax_ids': [Command.set(self.product_a.taxes_id.ids)]}),
            ],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        self.assertEqual(len(inv.line_ids), 5)  # 1 prod, 1 tax, 1 epd, 1 epd tax discount, 1 payment terms
        inv.write({'invoice_payment_term_id': self.pay_terms_a.id})
        self.assertEqual(len(inv.line_ids), 3)  # 1 prod, 1 tax, 1 payment terms
        inv.write({'invoice_payment_term_id': self.early_pay_10_percents_10_days.id})
        self.assertEqual(len(inv.line_ids), 5)

    def test_mixed_epd_with_tax_deleted_line(self):
        self.early_pay_10_percents_10_days.write({'early_pay_discount_computation': 'mixed'})
        tax_a = self.env['account.tax'].create({
             'name': 'Test A',
             'amount': 10,
        })
        tax_b = self.env['account.tax'].create({
             'name': 'Test B',
             'amount': 15,
        })

        inv = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [
                Command.create({'name': 'line', 'price_unit': 100.0, 'tax_ids': [Command.set(tax_a.ids)]}),
                Command.create({'name': 'line2', 'price_unit': 100.0, 'tax_ids': [Command.set(tax_b.ids)]}),
            ],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        self.assertEqual(len(inv.line_ids), 8)  # 2 prod, 2 tax, 1 epd, 2 epd tax discount, 1 payment terms
        inv.invoice_line_ids[1].unlink()
        self.assertEqual(len(inv.line_ids), 5)  # 1 prod, 1 tax, 1 epd, 1 epd tax discount, 1 payment terms
        self.assertEqual(inv.amount_tax, 9.00)  # $100.0 @ 10% tax (-10% epd)

    def test_mixed_epd_with_rounding_issue(self):
        """
        Ensure epd line will not unbalance the invoice
        """
        tax_6 = self.env['account.tax'].create({
             'name': '6%',
             'amount': 6,
        })
        tax_12 = self.env['account.tax'].create({
             'name': '12%',
             'amount': 12,
        })
        tax_136 = self.env['account.tax'].create({
             'name': '136',
             'amount': 0.136,
             'amount_type': 'fixed',
             'include_base_amount': True,
        })
        tax_176 = self.env['account.tax'].create({
             'name': '176',
             'amount': 0.176,
             'amount_type': 'fixed',
             'include_base_amount': True,
        })

        early_pay_1_percents_7_days = self.env['account.payment.term'].create({
            'name': '1% discount if paid within 7 days',
            'company_id': self.company_data['company'].id,
            'early_pay_discount_computation': 'mixed',
            'discount_percentage': 1,
            'discount_days': 7,
            'early_discount': True,
            'line_ids': [Command.create({
                'value': 'percent',
                'nb_days': 0,
                'value_amount': 100,
            })]
        })

        # The following vals will create a rounding issue
        line_create_vals = [
           (116, 6, tax_6),
           (0.91, 350, tax_6),
           (194.21, 1, tax_136 | tax_12),
           (31.46, 5, tax_176 | tax_12)
        ]

        # If invoice is not balanced the following create will fail
        self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2022-02-21',
            'invoice_payment_term_id': early_pay_1_percents_7_days.id,
            'invoice_line_ids': [
                Command.create({
                    'price_unit': price_unit,
                    'quantity': quantity,
                    'tax_ids': [Command.set(taxes.ids)]
                }) for price_unit, quantity, taxes in line_create_vals
            ]
        })

    def test_register_payment_batch_with_discount_and_without_discount(self):
        """
        Test that a batch payment, that is
            - not grouped
            - with invoices having different payment terms (1 with discount, 1 without)
        -> will not crash
        """
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.pay_term_net_30_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids

        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': False
        })._create_payments()
        self.assertTrue(all(payments.mapped('is_reconciled')))
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -2000.0},
            {'amount_currency': -1000.0},
            {'amount_currency': 200.0},
            {'amount_currency': 1000},
            {'amount_currency': 1800},
        ])

    def test_register_payment_batch_without_discount(self):
        """
        Test that a batch payment, that is
            - not grouped
            - with invoices having the same payment terms (without discount)
        -> will not crash
        """
        out_invoice_1 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.pay_term_net_30_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.other_currency.id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.pay_term_net_30_days.id,
        })
        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids

        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': False
        })._create_payments()
        self.assertTrue(all(payments.mapped('is_reconciled')))
        self.assertRecordValues(payments.move_id.line_ids.sorted('balance'), [
            {'amount_currency': -2000.0},
            {'amount_currency': -1000.0},
            {'amount_currency': 1000.0},
            {'amount_currency': 2000},
        ])

    def test_mixed_epd_with_tax_refund(self):
        """
        Ensure epd line are addeed to refunds
        """
        self.early_pay_10_percents_10_days.write({'early_pay_discount_computation': 'mixed'})

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2022-02-21',
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
            'invoice_line_ids': [
                Command.create({
                    'price_unit': 100.0,
                    'quantity': 1,
                    'tax_ids': [Command.set(self.product_a.taxes_id.ids)],
                })
            ]
        })
        invoice.action_post()

        move_reversal = self.env['account.move.reversal'].with_context(active_model="account.move", active_ids=invoice.ids).create({
            'date': fields.Date.from_string('2017-01-01'),
            'reason': 'no reason again',
            'journal_id': invoice.journal_id.id,
        })

        receivable_line = invoice.line_ids.filtered(lambda x: x.account_id.account_type == 'asset_receivable')
        reversal = move_reversal.modify_moves()
        reverse_move = self.env['account.move'].browse(reversal['res_id'])

        self.assertEqual(invoice.payment_state, 'reversed', "After cancelling it with a reverse invoice, an invoice should be in 'reversed' state.")

        self.assertRecordValues(reverse_move.line_ids.sorted('id'), [
            {
                'balance': -100.0,
                'tax_base_amount': 0.0,
                'display_type': 'product',
            },
            {
                'balance': 10.0,
                'tax_base_amount': 0.0,
                'display_type': 'epd',
            },
            {
                'balance': -10.0,
                'tax_base_amount': 0.0,
                'display_type': 'epd',
            },
            {
                'balance': -13.5,
                'tax_base_amount': -90.0,
                'display_type': 'tax',
            },
            {
                'balance': receivable_line.balance,
                'tax_base_amount': 0.0,
                'display_type': 'payment_term',
            },
        ])

    def test_epd_validation_on_payment_terms(self):
        """
        Test that enabling Early Payment Discount (EPD) on payment terms with multiple lines raises a ValidationError,
        and that enabling EPD on payment terms with a single line does not raise any error.
        """
        payment_term = self.env['account.payment.term'].create({
            'name': 'Test Term',
            'line_ids': [
                Command.create({'value': 'percent', 'value_amount': 50, 'nb_days': 30}),
                Command.create({'value': 'percent', 'value_amount': 50, 'nb_days': 60}),
            ]
        })

        with self.assertRaisesRegex(
            ValidationError,
            "The Early Payment Discount functionality can only be used with payment terms using a single 100% line.",
            msg="EPD should not be allowed with multiple term lines",
        ):
            payment_term.early_discount = True

        # Modify the payment term to have a single line
        payment_term.line_ids = [
            Command.clear(),
            Command.create({"value": "percent", "value_amount": 100, "nb_days": 30}),
        ]

        try:
            payment_term.early_discount = True
        except ValidationError:
            self.fail(
                "ValidationError raised unexpectedly for single-line payment term with EPD"
            )

    def test_epd_multiple_repartition_lines(self):
        """
        In the case of multi repartition lines tax definition with an early payment discount
        We want to make sure that the EPD lines are correct.
        We want the rounding difference to be added to the "biggest" base line.
        """
        # Taxes.
        common_values = {
            'amount': 17.0,
            'invoice_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
            'refund_repartition_line_ids': [
                Command.create({'repartition_type': 'base'}),
                Command.create({'repartition_type': 'tax', 'factor_percent': 100.0}),
                Command.create({'repartition_type': 'tax', 'factor_percent': -100.0}),
            ],
        }

        tax1, tax2 = self.env['account.tax'].create([
            {'name': "tax1", **common_values},
            {'name': "tax2", **common_values},
        ])

        # Early payment.
        payment_term = self.env['account.payment.term'].create({
            'name': "10% discount if paid within 10 days",
            'early_discount': True,
            'early_pay_discount_computation': 'included',
            'discount_percentage': 2,
            'discount_days': 10,
            'line_ids': [Command.create({
                'value': 'percent',
                'nb_days': 0,
                'value_amount': 100,
            })]
        })

        # Invoice.
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_payment_term_id': payment_term.id,
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'name': "Line One",
                    'price_unit': 739.95,
                    'tax_ids': [Command.set(tax1.ids)],
                }),
                Command.create({
                    'name': "Line Two",
                    'price_unit': 37.80,
                    'tax_ids': [Command.set(tax2.ids)],
                }),
            ],
        })
        invoice.action_post()

        # Payment.
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({'payment_date': '2017-01-01'})\
            ._create_payments()

        self.assertRecordValues(payment.move_id.line_ids.sorted('amount_currency'), [
            # Invoice's total:
            {'amount_currency': -777.75},
            # Base / tax lines:
            {'amount_currency': -2.51},
            {'amount_currency': -0.13},
            {'amount_currency': 0.13},
            {'amount_currency': 0.76},
            {'amount_currency': 2.51},
            {'amount_currency': 14.79},
            # Discounted amount:
            {'amount_currency': 762.2},
        ])

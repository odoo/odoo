# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
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

    def assert_tax_totals(self, document, expected_values):
        main_keys_to_ignore = {
            'formatted_amount_total', 'formatted_amount_untaxed', 'display_tax_base', 'subtotals_order'}
        group_keys_to_ignore = {'group_key', 'tax_group_id', 'tax_group_name',
                                'formatted_tax_group_amount', 'formatted_tax_group_base_amount'}
        subtotals_keys_to_ignore = {'formatted_amount'}
        to_compare = document.copy()
        for key in main_keys_to_ignore:
            del to_compare[key]
        for key in group_keys_to_ignore:
            for groups in to_compare['groups_by_subtotal'].values():
                for group in groups:
                    del group[key]
        for key in subtotals_keys_to_ignore:
            for subtotal in to_compare['subtotals']:
                del subtotal[key]
        self.assertEqual(to_compare, expected_values)

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

    def test_invoice_report_without_invoice_date(self):
        """
        Ensure that an invoice with an early discount payment term
        and no invoice date can be previewed or printed.
        """
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)
        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
            'invoice_line_ids': [Command.create({
                'name': 'line1',
            })]
        }])

        # Assert that the invoice date is not set
        self.assertEqual(out_invoice.invoice_date, False)

        report = self.env['ir.actions.report'].with_context(force_report_rendering=True)._render_qweb_pdf('account.account_invoices', res_ids=out_invoice.id)
        self.assertTrue(report)

        #Test for invoices with multiple due dates and no early discount
        out_invoice.invoice_payment_term_id = self.pay_30_percents_now_balance_60_days
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
            {'display_type': 'tax',             'balance': -150},
            {'display_type': 'tax',             'balance': 15.0},
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
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.early_pay_10_percents_10_days.id,
        })
        out_invoice_1.action_post()
        active_ids = out_invoice_1.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-02',
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
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -1552.55, 'tax_tag_invert': False},
            {'amount_currency': -150.0, 'tax_tag_invert': True},
            {'amount_currency': -22.5, 'tax_tag_invert': True},
            {'amount_currency': 1725.05, 'tax_tag_invert': False},
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
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -51.80, 'tax_tag_invert': False},
            {'amount_currency': -5.00, 'tax_tag_invert': True},
            {'amount_currency': -0.75, 'tax_tag_invert': True},
            {'amount_currency': 57.55, 'tax_tag_invert': False},
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
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -1552.5, 'tax_tag_invert': False},
            {'amount_currency': -150.0, 'tax_tag_invert': True},
            {'amount_currency': -22.5, 'tax_tag_invert': True},
            {'amount_currency': 1725.0, 'tax_tag_invert': False},
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
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -1725.0, 'tax_tag_invert': False},
            {'amount_currency': 22.5, 'tax_tag_invert': False},
            {'amount_currency': 150.0, 'tax_tag_invert': False},
            {'amount_currency': 1552.5, 'tax_tag_invert': False},
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
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -2835.0, 'tax_tag_invert': False},
            {'amount_currency': -200.0, 'tax_tag_invert': False},
            {'amount_currency': -100.0, 'tax_tag_invert': True},
            {'amount_currency': -15.0, 'tax_tag_invert': True},
            {'amount_currency': 3150.0, 'tax_tag_invert': False},
        ])

    def test_register_payment_batch_included(self):
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'included'
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
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'excluded'
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
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'mixed'
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
        self.early_pay_10_percents_10_days.early_pay_discount_computation = 'mixed'
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
            self.assert_tax_totals(invoice.tax_totals, {
                'amount_untaxed': 1000,
                'amount_total': 1090,
                'groups_by_subtotal': {
                    'Untaxed Amount': [
                        {
                            'tax_group_amount': 90,
                            'tax_group_base_amount': 900,
                        },
                    ],
                },
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'amount': 1000,
                    }
                ],
            })

    def test_intracomm_bill_with_early_payment_included(self):
        tax_tags = self.env['account.account.tag'].create({
            'name': f'tax_tag_{i}',
            'applicability': 'taxes',
            'country_id': self.env.company.account_fiscal_country_id.id,
        } for i in range(6))

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

        self.assertRecordValues(payment.line_ids.sorted('balance'), [
            # pylint: disable=bad-whitespace
            {'amount_currency': -980.0, 'tax_ids': [],                  'tax_tag_ids': [],              'tax_tag_invert': False},
            {'amount_currency': -20.0,  'tax_ids': intracomm_tax.ids,   'tax_tag_ids': tax_tags[3].ids, 'tax_tag_invert': True},
            {'amount_currency': -4.0,   'tax_ids': [],                  'tax_tag_ids': tax_tags[4].ids, 'tax_tag_invert': True},
            {'amount_currency': 4.0,    'tax_ids': [],                  'tax_tag_ids': tax_tags[5].ids, 'tax_tag_invert': True},
            {'amount_currency': 1000.0, 'tax_ids': [],                  'tax_tag_ids': [],              'tax_tag_invert': False},
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
            'price_include': True,
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
            self.assert_tax_totals(invoice.tax_totals, {
                'amount_untaxed': 100,
                'amount_total': 120.58,
                'groups_by_subtotal': {
                    'Untaxed Amount': [
                        {
                            'tax_group_amount': 20.58,
                            'tax_group_base_amount': 98,
                        },
                    ],
                },
                'subtotals': [
                    {
                        'name': "Untaxed Amount",
                        'amount': 100,
                    }
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
        self.assertEqual(len(inv.line_ids), 6) # 1 prod, 1 tax, 2 epd, 1 epd tax discount, 1 payment terms
        inv.write({'invoice_payment_term_id': self.pay_terms_a.id})
        self.assertEqual(len(inv.line_ids), 3) # 1 prod, 1 tax, 1 payment terms
        inv.write({'invoice_payment_term_id': self.early_pay_10_percents_10_days.id})
        self.assertEqual(len(inv.line_ids), 6)

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
        self.assertEqual(len(inv.line_ids), 10) # 2 prod, 2 tax, 3 epd, 2 epd tax discount, 1 payment terms
        inv.invoice_line_ids[1].unlink()
        self.assertEqual(len(inv.line_ids), 6) # 1 prod, 1 tax, 2 epd, 1 epd tax discount, 1 payment terms
        self.assertEqual(inv.amount_tax, 9.00) # $100.0 @ 10% tax (-10% epd)

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
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.pay_term_net_30_days.id,
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
            'payment_date': '2019-01-01', 'group_payment': False
        })._create_payments()
        self.assertTrue(all(payments.mapped('is_reconciled')))
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
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
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.pay_term_net_30_days.id,
        })
        out_invoice_2 = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2019-01-01',
            'invoice_date': '2019-01-01',
            'partner_id': self.partner_a.id,
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [Command.create({'product_id': self.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': self.pay_term_net_30_days.id,
        })
        (out_invoice_1 + out_invoice_2).action_post()
        active_ids = (out_invoice_1 + out_invoice_2).ids

        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2019-01-01', 'group_payment': False
        })._create_payments()
        self.assertTrue(all(payments.mapped('is_reconciled')))
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
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
                'balance': -15.0,
                'tax_base_amount': 100.0,
                'display_type': 'tax',
            },
            {
                'balance': 1.5,
                'tax_base_amount': -10.0,
                'display_type': 'tax',
            },
            {
                'balance': receivable_line.balance,
                'tax_base_amount': 0.0,
                'display_type': 'payment_term',
            },
        ])

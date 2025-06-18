# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
from odoo.exceptions import UserError, ValidationError
from odoo import Command


@tagged('post_install', '-at_install')
class TestAccountAnalyticAccount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.env.user.groups_id += cls.env.ref('analytic.group_analytic_accounting')

        # By default, tests are run with the current user set on the first company.
        cls.env.user.company_id = cls.company_data['company']

        cls.default_plan = cls.env['account.analytic.plan'].create({'name': 'Default', 'company_id': False})
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
        cls.analytic_account_c = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_c',
            'plan_id': cls.default_plan.id,
            'company_id': False,
        })
        cls.analytic_account_d = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_d',
            'plan_id': cls.default_plan.id,
            'company_id': False,
        })

    def get_analytic_lines(self, invoice):
        return self.env['account.analytic.line'].search([
            ('move_line_id', 'in', invoice.line_ids.ids),
        ]).sorted('amount')

    def create_invoice(self, partner, product, move_type='out_invoice'):
        return self.env['account.move'].create([{
            'move_type': move_type,
            'partner_id': partner.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': product.id,
            })]
        }])

    def test_changing_analytic_company(self):
        """ Ensure you can't change the company of an account.analytic.account if there are analytic lines linked to
            the account
        """
        self.env['account.analytic.line'].create({
            'name': 'company specific account',
            'account_id': self.analytic_account_a.id,
            'amount': 100,
        })

        # Set a different company on the analytic account.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.analytic_account_a.company_id = self.company_data_2['company']

        # Making the analytic account not company dependent is allowed.
        self.analytic_account_a.company_id = False

    def test_analytic_lines(self):
        ''' Ensures analytic lines are created when posted and are recreated when editing the account.move'''

        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 200.0,
                'analytic_distribution': {
                    self.analytic_account_a.id: 100,
                    self.analytic_account_b.id: 50,
                },
            })]
        }])

        out_invoice.action_post()

        # Analytic lines are created when posting the invoice
        self.assertRecordValues(self.get_analytic_lines(out_invoice), [{
            'amount': 100,
            'account_id': self.analytic_account_b.id,
        }, {
            'amount': 200,
            'account_id': self.analytic_account_a.id,
            'partner_id': self.partner_a.id,
            'product_id': self.product_a.id,
        }])

        # Analytic lines are updated when a posted invoice's distribution changes
        out_invoice.invoice_line_ids.analytic_distribution = {
            self.analytic_account_a.id: 100,
            self.analytic_account_b.id: 25,
        }
        self.assertRecordValues(self.get_analytic_lines(out_invoice), [{
            'amount': 50,
            'account_id': self.analytic_account_b.id,
        }, {
            'amount': 200,
            'account_id': self.analytic_account_a.id,
        }])

        # Analytic lines are deleted when resetting to draft
        out_invoice.button_draft()
        self.assertFalse(self.get_analytic_lines(out_invoice))

    def test_analytic_lines_rounding(self):
        """ Ensures analytic lines rounding errors are spread across all lines, in such a way that summing them gives the right amount.
        For example, when distributing 100% of the the price, the sum of analytic lines should be exactly equal to the price. """

        # in this scenario,
        # 94% of 182.25 = 171.315 rounded to 171.32
        # 2% of 182.25 = 3.645 rounded to 3.65
        # 3 * 3.65 + 171.32 = 182.27
        # we remove 0.01 to two lines to counter the rounding errors.
        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 182.25,
                'analytic_distribution': {
                    self.analytic_account_a.id: 94,
                    self.analytic_account_b.id: 2,
                    self.analytic_account_c.id: 2,
                    self.analytic_account_d.id: 2,
                },
            })]
        }])

        out_invoice.action_post()

        self.assertRecordValues(self.get_analytic_lines(out_invoice), [
            {
                'amount': 3.64,
                'account_id': self.analytic_account_b.id,
            },
            {
                'amount': 3.65,
                'account_id': self.analytic_account_d.id,
            },
            {
                'amount': 3.65,
                'account_id': self.analytic_account_c.id,
            },
            {
                'amount': 171.31,
                'account_id': self.analytic_account_a.id,
            },
        ])

        out_invoice.button_draft()
        # in this scenario,
        # 25% of 182.25 = 45.5625 rounded to 45.56
        # 45.56 * 4 = 182.24
        # we add 0.01 to one of the line to counter the rounding errors.
        out_invoice.invoice_line_ids[0].analytic_distribution = {
            self.analytic_account_a.id: 25,
            self.analytic_account_b.id: 25,
            self.analytic_account_c.id: 25,
            self.analytic_account_d.id: 25,
        }
        out_invoice.action_post()

        self.assertRecordValues(self.get_analytic_lines(out_invoice), [
            {
                'amount': 45.56,
                'account_id': self.analytic_account_d.id,
            },
            {
                'amount': 45.56,
                'account_id': self.analytic_account_c.id,
            },
            {
                'amount': 45.56,
                'account_id': self.analytic_account_b.id,
            },
            {
                'amount': 45.57,
                'account_id': self.analytic_account_a.id,
            },
        ])

    def test_model_score(self):
        """Test that the models are applied correctly based on the score"""

        self.env['account.analytic.distribution.model'].create([{
            'product_id': self.product_a.id,
            'analytic_distribution': {self.analytic_account_a.id: 100}
        }, {
            'partner_id': self.partner_a.id,
            'product_id': self.product_a.id,
            'analytic_distribution': {self.analytic_account_b.id: 100}
        }])

        # Partner and product match, score 2
        invoice = self.create_invoice(self.partner_a, self.product_a)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_b.id): 100})

        # Match the partner but not the product, score 0
        invoice = self.create_invoice(self.partner_a, self.product_b)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

        # Product match, score 1
        invoice = self.create_invoice(self.partner_b, self.product_a)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_a.id): 100})

        # No rule match with the product, score 0
        invoice = self.create_invoice(self.partner_b, self.product_b)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

    def test_model_application(self):
        """Test that the distribution is recomputed if and only if it is needed when changing the partner."""
        self.env['account.analytic.distribution.model'].create([{
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account_a.id: 100},
            'company_id': False,
        }, {
            'partner_id': self.partner_b.id,
            'analytic_distribution': {self.analytic_account_b.id: 100},
            'company_id': False,
        }])

        invoice = self.create_invoice(self.env['res.partner'], self.product_a)
        # No model is found, don't put anything
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

        # A model is found, set the new values
        invoice.partner_id = self.partner_a
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_a.id): 100})

        # A model is found, set the new values
        invoice.partner_id = self.partner_b
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_b.id): 100})

        # No model is found, don't change previously set values
        invoice.partner_id = invoice.company_id.partner_id
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_b.id): 100})

        # No model is found, don't change previously set values
        invoice.partner_id = False
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_b.id): 100})

        # It manual value is not erased in form view when saving
        with Form(invoice) as invoice_form:
            invoice_form.partner_id = self.partner_a
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                self.assertEqual(line_form.analytic_distribution, {str(self.analytic_account_a.id): 100})
                line_form.analytic_distribution = {self.analytic_account_b.id: 100}
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_b.id): 100})

    def test_mandatory_plan_validation(self):
        invoice = self.create_invoice(self.partner_b, self.product_a)
        self.default_plan.write({
            'applicability_ids': [Command.create({
                'business_domain': 'invoice',
                'product_categ_id': self.product_a.categ_id.id,
                'applicability': 'mandatory',
            })]
        })

        # ValidationError is raised only when validate_analytic is in the context and the distribution is != 100
        with self.assertRaisesRegex(ValidationError, '100% analytic distribution.'):
            invoice.with_context({'validate_analytic': True}).action_post()

        invoice.invoice_line_ids.analytic_distribution = {self.analytic_account_b.id: 100.01}
        with self.assertRaisesRegex(ValidationError, '100% analytic distribution.'):
            invoice.with_context({'validate_analytic': True}).action_post()

        invoice.invoice_line_ids.analytic_distribution = {self.analytic_account_b.id: 99.9}
        with self.assertRaisesRegex(ValidationError, '100% analytic distribution.'):
            invoice.with_context({'validate_analytic': True}).action_post()

        invoice.invoice_line_ids.analytic_distribution = {self.analytic_account_b.id: 100}
        invoice.with_context({'validate_analytic': True}).action_post()
        self.assertEqual(invoice.state, 'posted')

        # reset and post without the validate_analytic context key
        invoice.button_draft()
        invoice.invoice_line_ids.analytic_distribution = {self.analytic_account_b.id: 0.9}
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

    def test_mandatory_plan_validation_mass_posting(self):
        """
        In case of mass posting, we should still check for mandatory analytic plans. This may raise a RedirectWarning,
        if more than one entry was selected for posting, or a ValidationError if only one entry was selected.
        """
        invoice1 = self.create_invoice(self.partner_a, self.product_a)
        invoice2 = self.create_invoice(self.partner_b, self.product_a)
        self.default_plan.write({
            'applicability_ids': [Command.create({
                'business_domain': 'invoice',
                'product_categ_id': self.product_a.categ_id.id,
                'applicability': 'mandatory',
            })]
        })

        vam = self.env['validate.account.move'].create({'force_post': True})
        for invoices in [invoice1, invoice1 | invoice2]:
            with self.subTest(invoices=invoices):
                with self.assertRaises(Exception):
                    vam.with_context({
                        'active_model': 'account.move',
                        'active_ids': [invoice1.id, invoice2.id],
                        'validate_analytic': True,
                    }).validate_move()
                self.assertTrue('posted' not in invoices.mapped('state'))

    def test_set_anaylytic_distribution_posted_line(self):
        """
        Test that we can set the analytic distribution on the product line of a move, when the line has tax with
        repartition lines used in tax closing. Although the change can not be applied on the tax line, we should
        not raise any error.
        """
        tax = self.tax_purchase_a.copy({
            'name': 'taXXX',
            'invoice_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'use_in_tax_closing': False,
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 50,
                    'use_in_tax_closing': False,
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 50,
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                    'use_in_tax_closing': True,
                }),
            ],
            'refund_repartition_line_ids': [
                Command.create({
                    'repartition_type': 'base',
                    'use_in_tax_closing': False,
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 50,
                    'use_in_tax_closing': False,
                }),
                Command.create({
                    'repartition_type': 'tax',
                    'factor_percent': 50,
                    'account_id': self.company_data['default_account_tax_purchase'].id,
                    'use_in_tax_closing': True,
                }),
            ],
        })

        bill = self.create_invoice(self.partner_a, self.product_a, move_type='in_invoice')
        bill.invoice_line_ids.tax_ids = [Command.set(tax.ids)]
        bill.action_post()

        line = bill.line_ids.filtered(lambda l: l.display_type == 'product')
        line.write({'analytic_distribution': {self.analytic_account_a.id: 100}})
        self.assertEqual(line.analytic_distribution, {str(self.analytic_account_a.id): 100})

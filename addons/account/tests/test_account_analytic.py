# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged, Form
from odoo.exceptions import UserError
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
        })
        cls.analytic_account_b = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_b',
            'plan_id': cls.default_plan.id,
        })

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
        def get_analytic_lines():
            return self.env['account.analytic.line'].search([
                ('move_line_id', 'in', out_invoice.line_ids.ids)
            ]).sorted('amount')

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
        self.assertRecordValues(get_analytic_lines(), [{
            'amount': 100,
            'account_id': self.analytic_account_b.id,
            'partner_id': self.partner_a.id,
            'product_id': self.product_a.id,
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
        self.assertRecordValues(get_analytic_lines(), [{
            'amount': 50,
            'account_id': self.analytic_account_b.id,
        }, {
            'amount': 200,
            'account_id': self.analytic_account_a.id,
        }])

        # Analytic lines are deleted when resetting to draft
        out_invoice.button_draft()
        self.assertFalse(get_analytic_lines())

    def test_plan_score(self):
        """Test that the plans are applied correctly based on the score"""
        def create_invoice(partner, product):
            return self.env['account.move'].create([{
                'move_type': 'out_invoice',
                'partner_id': partner.id,
                'date': '2017-01-01',
                'invoice_date': '2017-01-01',
                'invoice_line_ids': [Command.create({
                    'product_id': product.id,
                })]
            }])

        self.env['account.analytic.distribution.model'].create([{
            'product_id': self.product_a.id,
            'analytic_distribution': {self.analytic_account_a.id: 100}
        }, {
            'partner_id': self.partner_a.id,
            'product_id': self.product_a.id,
            'analytic_distribution': {self.analytic_account_b.id: 100}
        }])

        # Partner and product match, score 2
        invoice = create_invoice(self.partner_a, self.product_a)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {self.analytic_account_b.id: 100})

        # Match the partner but not the product, score 0
        invoice = create_invoice(self.partner_a, self.product_b)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

        # Product match, score 1
        invoice = create_invoice(self.partner_b, self.product_a)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {self.analytic_account_a.id: 100})

        # No rule match with the product, score 0
        invoice = create_invoice(self.partner_b, self.product_b)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

    def test_plan_application(self):
        """Test that the distribution is recomputed if and only if it is needed when changing the partner."""
        self.env['account.analytic.distribution.model'].create([{
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account_a.id: 100}
        }, {
            'partner_id': self.partner_b.id,
            'analytic_distribution': {self.analytic_account_b.id: 100}
        }])

        invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
            })]
        }])
        # No model is found, don't put anything
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

        # A model is found, set the new values
        invoice.partner_id = self.partner_a
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {self.analytic_account_a.id: 100})

        # A model is found, set the new values
        invoice.partner_id = self.partner_b
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {self.analytic_account_b.id: 100})

        # No model is found, don't change previously set values
        invoice.partner_id = invoice.company_id.partner_id
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {self.analytic_account_b.id: 100})

        # No model is found, don't change previously set values
        invoice.partner_id = False
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {self.analytic_account_b.id: 100})

        # It manual value is not erased in form view when saving
        with Form(invoice) as invoice_form:
            invoice_form.partner_id = self.partner_a
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                self.assertEqual(line_form.analytic_distribution, {self.analytic_account_a.id: 100})
                line_form.analytic_distribution = {self.analytic_account_b.id: 100}
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {self.analytic_account_b.id: 100})

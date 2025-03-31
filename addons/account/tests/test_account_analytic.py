from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.addons.analytic.tests.common import AnalyticCommon
from odoo.tests import tagged, Form
from odoo.exceptions import UserError, ValidationError
from odoo import Command


@tagged('post_install', '-at_install')
class TestAccountAnalyticAccount(AccountTestInvoicingCommon, AnalyticCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data_2 = cls.setup_other_company()

        cls.cross_plan = cls.env['account.analytic.plan'].create({'name': 'Cross'})
        cls.analytic_account_5 = cls.env['account.analytic.account'].create({
            'name': 'analytic_account_5',
            'plan_id': cls.cross_plan.id,
            'company_id': False,
        })

    def create_invoice(self, partner, product):
        return self.env['account.move'].create([{
            'move_type': 'out_invoice',
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
            'account_id': self.analytic_account_3.id,
            'amount': 100,
        })

        # Set a different company on the analytic account.
        with self.assertRaises(UserError), self.cr.savepoint():
            self.analytic_account_3.company_id = self.company_data_2['company']

        # Making the analytic account not company dependent is allowed.
        self.analytic_account_3.company_id = False

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
                    self.analytic_account_3.id: 100,
                    self.analytic_account_4.id: 50,
                },
            })]
        }])

        out_invoice.action_post()

        # Analytic lines are created when posting the invoice
        self.assertRecordValues(get_analytic_lines(), [{
            'amount': 100,
            self.analytic_plan_2._column_name(): self.analytic_account_4.id,
            'partner_id': self.partner_a.id,
            'product_id': self.product_a.id,
        }, {
            'amount': 200,
            self.analytic_plan_2._column_name(): self.analytic_account_3.id,
            'partner_id': self.partner_a.id,
            'product_id': self.product_a.id,
        }])

        # Analytic lines are updated when a posted invoice's distribution changes
        out_invoice.invoice_line_ids.analytic_distribution = {
            self.analytic_account_3.id: 100,
            self.analytic_account_4.id: 25,
        }
        self.assertRecordValues(get_analytic_lines(), [{
            'amount': 50,
            self.analytic_plan_2._column_name(): self.analytic_account_4.id,
        }, {
            'amount': 200,
            self.analytic_plan_2._column_name(): self.analytic_account_3.id,
        }])

        # Analytic lines are deleted when resetting to draft
        out_invoice.button_draft()
        self.assertFalse(get_analytic_lines())

    def test_model_score(self):
        """Test that the models are applied correctly based on the score"""

        self.env['account.analytic.distribution.model'].create([{
            'product_id': self.product_a.id,
            'analytic_distribution': {self.analytic_account_3.id: 100}
        }, {
            'partner_id': self.partner_a.id,
            'product_id': self.product_a.id,
            'analytic_distribution': {self.analytic_account_4.id: 100}
        }])

        # Partner and product match, score 2
        invoice = self.create_invoice(self.partner_a, self.product_a)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_4.id): 100})

        # Match the partner but not the product, score 0
        invoice = self.create_invoice(self.partner_a, self.product_b)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

        # Product match, score 1
        invoice = self.create_invoice(self.partner_b, self.product_a)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_3.id): 100})

        # No rule match with the product, score 0
        invoice = self.create_invoice(self.partner_b, self.product_b)
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

    def test_model_application(self):
        """Test that the distribution is recomputed if and only if it is needed when changing the partner."""
        self.env['account.analytic.distribution.model'].create([{
            'partner_id': self.partner_a.id,
            'analytic_distribution': {self.analytic_account_3.id: 100},
            'company_id': False,
        }, {
            'partner_id': self.partner_b.id,
            'analytic_distribution': {self.analytic_account_4.id: 100},
            'company_id': False,
        }])

        invoice = self.create_invoice(self.env['res.partner'], self.product_a)
        # No model is found, don't put anything
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)

        # A model is found, set the new values
        invoice.partner_id = self.partner_a
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_3.id): 100})

        # A model is found, set the new values
        invoice.partner_id = self.partner_b
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_4.id): 100})

        # No model is found, don't change previously set values
        invoice.partner_id = invoice.company_id.partner_id
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_4.id): 100})

        # No model is found, don't change previously set values
        invoice.partner_id = False
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_4.id): 100})

        # It manual value is not erased in form view when saving
        with Form(invoice) as invoice_form:
            invoice_form.partner_id = self.partner_a
            with invoice_form.invoice_line_ids.edit(0) as line_form:
                self.assertEqual(line_form.analytic_distribution, {str(self.analytic_account_3.id): 100})
                line_form.analytic_distribution = {self.analytic_account_4.id: 100}
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_4.id): 100})

    def test_mandatory_plan_validation(self):
        invoice = self.create_invoice(self.partner_b, self.product_a)
        self.analytic_plan_2.write({
            'applicability_ids': [Command.create({
                'business_domain': 'invoice',
                'product_categ_id': self.product_a.categ_id.id,
                'applicability': 'mandatory',
            })]
        })

        # ValidationError is raised only when validate_analytic is in the context and the distribution is != 100
        with self.assertRaisesRegex(ValidationError, '100% analytic distribution.'):
            invoice.with_context({'validate_analytic': True}).action_post()

        invoice.invoice_line_ids.analytic_distribution = {self.analytic_account_4.id: 100.01}
        with self.assertRaisesRegex(ValidationError, '100% analytic distribution.'):
            invoice.with_context({'validate_analytic': True}).action_post()

        invoice.invoice_line_ids.analytic_distribution = {self.analytic_account_4.id: 99.9}
        with self.assertRaisesRegex(ValidationError, '100% analytic distribution.'):
            invoice.with_context({'validate_analytic': True}).action_post()

        invoice.invoice_line_ids.analytic_distribution = {self.analytic_account_4.id: 100}
        invoice.with_context({'validate_analytic': True}).action_post()
        self.assertEqual(invoice.state, 'posted')

        # reset and post without the validate_analytic context key
        invoice.button_draft()
        invoice.invoice_line_ids.analytic_distribution = {self.analytic_account_4.id: 0.9}
        invoice.action_post()
        self.assertEqual(invoice.state, 'posted')

    def test_mandatory_plan_validation_mass_posting(self):
        """
        In case of mass posting, we should still check for mandatory analytic plans. This may raise a RedirectWarning,
        if more than one entry was selected for posting, or a ValidationError if only one entry was selected.
        """
        invoice1 = self.create_invoice(self.partner_a, self.product_a)
        invoice2 = self.create_invoice(self.partner_b, self.product_a)
        self.analytic_plan_2.write({
            'applicability_ids': [Command.create({
                'business_domain': 'invoice',
                'product_categ_id': self.product_a.categ_id.id,
                'applicability': 'mandatory',
            })]
        })

        vam = self.env['validate.account.move'].with_context({
            'active_model': 'account.move',
            'active_ids': [invoice1.id, invoice2.id],
            'validate_analytic': True,
        }).create({'force_post': True})
        for invoices in [invoice1, invoice1 | invoice2]:
            with self.subTest(invoices=invoices):
                with self.assertRaises(Exception):
                    vam.validate_move()
                self.assertTrue('posted' not in invoices.mapped('state'))

    def test_cross_analytics_computing(self):

        out_invoice = self.env['account.move'].create([{
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [Command.create({
                'product_id': self.product_b.id,
                'price_unit': 200.0,
                'analytic_distribution': {
                    f'{self.analytic_account_3.id},{self.analytic_account_5.id}': 20,
                    f'{self.analytic_account_3.id},{self.analytic_account_4.id}': 80,
                },
            })]
        }])
        out_invoice.action_post()
        in_invoice = self.env['account.move'].create([{
            'move_type': 'in_invoice',
            'partner_id': self.partner_b.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'analytic_distribution': {
                        f'{self.analytic_account_3.id},{self.analytic_account_4.id}': 100,
                    },
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'analytic_distribution': {
                        f'{self.analytic_account_3.id},{self.analytic_account_5.id}': 50,
                        self.analytic_account_4.id: 50,
                    },
                })
            ]
        }])
        in_invoice.action_post()

        self.analytic_account_3._compute_invoice_count()
        self.assertEqual(self.analytic_account_3.invoice_count, 1)
        self.analytic_account_3._compute_vendor_bill_count()
        self.assertEqual(self.analytic_account_3.vendor_bill_count, 1)

    def test_applicability_score(self):
        """ Tests which applicability is chosen if several ones are valid """
        applicability_without_company, applicability_with_company = self.env['account.analytic.applicability'].create([
            {
                'business_domain': 'invoice',
                'product_categ_id': self.product_a.categ_id.id,
                'applicability': 'mandatory',
                'analytic_plan_id': self.analytic_plan_2.id,
                'company_id': False,
            },
            {
                'business_domain': 'invoice',
                'applicability': 'unavailable',
                'analytic_plan_id': self.analytic_plan_2.id,
                'company_id': self.env.company.id,
            },
        ])

        applicability = self.analytic_plan_2._get_applicability(business_domain='invoice', company_id=self.env.company.id, product=self.product_a.id)
        self.assertEqual(applicability, 'mandatory', "product takes precedence over company")

        # If the model that asks for a validation does not have a company_id,
        # the score shouldn't take into account the company of the applicability
        score = applicability_without_company._get_score(business_domain='invoice', product=self.product_a.id)
        self.assertEqual(score, 2)
        score = applicability_with_company._get_score(business_domain='invoice', product=self.product_a.id)
        self.assertEqual(score, 1)

    def test_model_sequence(self):
        plan_A, plan_B, plan_C = self.env['account.analytic.plan'].create([
            {'name': "Plan A"},
            {'name': "Plan B"},
            {'name': "Plan C"},
        ])
        aa_A1, aa_A2, aa_B1, aa_B3, aa_C2 = self.env['account.analytic.account'].create([
            {'name': "A1", 'plan_id': plan_A.id},
            {'name': "A2", 'plan_id': plan_A.id},
            {'name': "B1", 'plan_id': plan_B.id},
            {'name': "B3", 'plan_id': plan_B.id},
            {'name': "C2", 'plan_id': plan_C.id},
        ])
        m1, m2, m3 = self.env['account.analytic.distribution.model'].create([
            {'account_prefix': '123', 'sequence': 10, 'analytic_distribution': {f'{aa_A1.id},{aa_B1.id}': 100}},
            {'account_prefix': '123', 'sequence': 20, 'analytic_distribution': {f'{aa_A2.id},{aa_C2.id}': 100}},
            {'account_prefix': '123', 'sequence': 30, 'analytic_distribution': {f'{aa_B3.id}': 100}},
        ])
        criteria = {
            'account_prefix': '123456',
            'company_id': self.env.company.id,
        }

        # Priority: m1 > m2 > m3 : A1, B1
        distribution = self.env['account.analytic.distribution.model']._get_distribution(criteria)
        self.assertEqual(distribution, m1.analytic_distribution, 'm1 fills A & B, ignore m1 & m2')

        # Priority: m2 > m1 > m3 : A2, B3, C2
        m1.sequence, m2.sequence, m3.sequence = 2, 1, 3
        distribution = self.env['account.analytic.distribution.model']._get_distribution(criteria)
        self.assertEqual(distribution, m2.analytic_distribution | m3.analytic_distribution, 'm2 fills A, ignore m1')

        # Priority: m3 > m1 > m2 : A2, B3, C2
        m1.sequence, m2.sequence, m3.sequence = 2, 3, 1
        distribution = self.env['account.analytic.distribution.model']._get_distribution(criteria)
        self.assertEqual(distribution, m2.analytic_distribution | m3.analytic_distribution, 'm3 fills B, ignore m1')

    def test_analytic_distribution_multiple_prefixes(self):
        self.env['account.analytic.distribution.model'].create([{
            'account_prefix': '61;62',
            'analytic_distribution': {self.analytic_account_3.id: 100},
            'company_id': False,
        }, {
            'account_prefix': '63, 64',
            'analytic_distribution': {self.analytic_account_4.id: 100},
            'company_id': False,
        }])
        accounts_by_code = self.env['account.account'].search([('code', 'ilike', '6%')]).grouped('code')
        invoice = self.create_invoice(self.env['res.partner'], self.product_a)
        # No model is found, don't put anything
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, False)
        invoice.invoice_line_ids.account_id = accounts_by_code.get('611000')
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_3.id): 100})

        invoice.invoice_line_ids.account_id = accounts_by_code.get('630000')
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_4.id): 100})

        invoice.invoice_line_ids.account_id = accounts_by_code.get('620000')
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_3.id): 100})

        invoice.invoice_line_ids.account_id = accounts_by_code.get('641000')
        self.assertEqual(invoice.invoice_line_ids.analytic_distribution, {str(self.analytic_account_4.id): 100})

    def test_analytic_applicability_multiple_prefixes(self):
        # This applicability should block all invoices with lines having account_code who starts with '40' or '41'
        self.env['account.analytic.applicability'].create([
            {
                'business_domain': 'invoice',
                'applicability': 'mandatory',
                'analytic_plan_id': self.analytic_plan_2.id,
                'company_id': self.env.company.id,
                'account_prefix': '40, 41',
            }
        ])

        account_analytic = self.env['account.analytic.account'].search([('plan_id', '=', self.analytic_plan_2.id)], limit=1)

        account_invoice_1, account_invoice_2 = self.env['account.account'].create([
            {
                'code': '400300',
                'name': 'My first invoice Account',
            },
            {
                'code': '410300',
                'name': 'My second invoice Account',
            },
        ])

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_b.id,
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'invoice_line_ids': [
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'account_id': account_invoice_1.id,
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'price_unit': 200.0,
                    'account_id': account_invoice_2.id,
                })
            ]
        })

        # This invoice should be blocked as there is no analytic plans on lines
        with self.assertRaisesRegex(ValidationError, '100% analytic distribution.'):
            invoice.with_context({'validate_analytic': True}).action_post()

        invoice.line_ids.filtered(lambda line: line.account_id.code.startswith('40'))[0].write({
            'analytic_distribution': {account_analytic.id: 100}
        })

        # This invoice should be blocked because one line is missing plans
        with self.assertRaisesRegex(ValidationError, '100% analytic distribution.'):
            invoice.with_context({'validate_analytic': True}).action_post()

        invoice.line_ids.filtered(lambda line: line.account_id.code.startswith('41'))[0].write({
            'analytic_distribution': {account_analytic.id: 100}
        })

        # This invoice should not be blocked, as all lines have plans
        invoice.with_context({'validate_analytic': True}).action_post()

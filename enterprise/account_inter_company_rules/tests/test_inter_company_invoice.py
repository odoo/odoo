# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command, tests
from .common import TestInterCompanyRulesCommon


@tests.tagged('post_install', '-at_install')
class TestInterCompanyInvoice(TestInterCompanyRulesCommon):

    @classmethod
    def setUpClass(cls):
        super(TestInterCompanyInvoice, cls).setUpClass()
        # Enable auto generate invoice in company.
        (cls.company_a + cls.company_b).write({
            'intercompany_generate_bills_refund': True,
        })
        # Configure Chart of Account for company_b.
        cls.env.user.company_id = cls.company_b
        cls.env['account.chart.template'].try_loading('generic_coa', cls.company_b, install_demo=False)
        # Configure Chart of Account for company_a.
        cls.env.user.company_id = cls.company_a
        cls.env['account.chart.template'].try_loading('generic_coa', cls.company_a, install_demo=False)

    def _configure_analytic(self, product=None, company=None, partner=None):
        """
        Configure Analytic Distribution Model for company_a based on Product A
        return: analytic account
        """
        display_name = "Inter Company"
        if company:
            self.env.user.company_id = company
            display_name = company.display_name
        analytic_plan = self.env['account.analytic.plan'].create({'name': f'Analytic Plan {display_name}'})
        analytic_account = self.env['account.analytic.account'].create({
            'name': f'Account {display_name}',
            'company_id': company and company.id,
            'plan_id': analytic_plan.id,
        })
        self.env['account.analytic.distribution.model'].create({
            'analytic_distribution': {analytic_account.id: 100},
            'product_id': product and product.id,
            'company_id': company and company.id,
            'partner_id': partner and partner.id,
        })
        return analytic_account

    def _create_post_invoice(self, product_id, analytic_distribution=None):
        """Create a Company A invoice with Company B as the customer and post it"""
        invoice_line_vals = {
                'product_id': product_id,
                'price_unit': 100.0,
                'quantity': 1.0,
            }
        if analytic_distribution:
            invoice_line_vals['analytic_distribution'] = analytic_distribution

        customer_invoice = self.env['account.move'].with_user(self.res_users_company_a).create({
            'move_type': 'out_invoice',
            'partner_id': self.company_b.partner_id.id,
            'invoice_line_ids': [(0, 0, invoice_line_vals)]
        })
        customer_invoice.with_user(self.res_users_company_a).action_post()

    def test_00_inter_company_invoice_flow(self):
        """ Test inter company invoice flow """

        self.env.ref('base.EUR').active = True

        # Create customer invoice for company A. (No need to call onchange as all the needed values are specified)
        self.res_users_company_a.company_ids = [(4, self.company_b.id)]
        customer_invoice = self.env['account.move'].with_user(self.res_users_company_a).create({
            'move_type': 'out_invoice',
            'partner_id': self.company_b.partner_id.id,
            'currency_id': self.env.ref('base.EUR').id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_consultant.id,
                'price_unit': 450.0,
                'quantity': 1.0,
                'name': 'test'
            })]
        })

        # Check account invoice state should be draft.
        self.assertEqual(customer_invoice.state, 'draft', 'Initially customer invoice should be in the "Draft" state')

        # Validate invoice
        customer_invoice.with_user(self.res_users_company_a).action_post()

        # Check Invoice status should be open after validate.
        self.assertEqual(customer_invoice.state, 'posted', 'Invoice should be in Open state.')

        # I check that the vendor bill is created with proper data.
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)

        self.assertTrue(supplier_invoice.invoice_line_ids[0].quantity == 1, "Quantity in invoice line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].product_id.id == self.product_consultant.id, "Product in line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].price_unit == 450, "Unit Price in invoice line is incorrect.")
        self.assertTrue(supplier_invoice.invoice_line_ids[0].account_id.company_ids == self.company_b, "Applied account in created invoice line is not relevant to company.")
        self.assertTrue(supplier_invoice.state == "draft", "invoice should be in draft state.")
        self.assertEqual(supplier_invoice.amount_total, 517.5, "Total amount is incorrect.")
        self.assertTrue(supplier_invoice.company_id.id == self.company_b.id, "Applied company in created invoice is incorrect.")

    def test_default_analytic_distribution_company_b(self):
        """
        [Analytic Distribution Model is set for Company B + Inter Company Analytic Account is set]
        - With Company A, create an Invoice for Company B with product A set with an analytic distribution model available for Company B
        -> The Analytic Distribution set on the Supplier Invoice Line should be the same as defined in the analytic distribution model set by default for Company B
        and the one manually set when the analytic account is also available for Company B
        """
        analytic_account_company_b = self._configure_analytic(company=self.company_b, product=self.product_a)
        inter_company_analytic_account = self._configure_analytic(product=self.product_b)

        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={inter_company_analytic_account.id: 100})
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)

        self.assertEqual(supplier_invoice.invoice_line_ids.analytic_distribution, {str(analytic_account_company_b.id): 100, str(inter_company_analytic_account.id): 100})

    def test_no_default_analytic_distribution_company_b(self):
        """
        [Analytic Distribution Model is not set for Company B + Inter Company Analytic Account is set]
        - With Company A, create an Invoice for Company B with a line set with an analytic distribution model available for Company B
        -> The analytic distribution set on the supplier invoice line should be the same as defined in the customer invoice line created in Company A
        as the analytic account is available for Company B and there are no default analytic distribution model set for Company B
        """
        inter_company_analytic_account = self._configure_analytic(product=self.product_b)

        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={inter_company_analytic_account.id: 100})
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)

        self.assertEqual(supplier_invoice.invoice_line_ids.analytic_distribution, {str(inter_company_analytic_account.id): 100})

    def test_multi_analytic_account_distribution_company_b(self):
        """
        Test that the analytic distribution is set properly when multiple analytic accounts (with or without a company) are set on the invoice line
        """
        analytic_account_company_a = self._configure_analytic(company=self.company_a, product=self.product_a)
        inter_company_analytic_account = self._configure_analytic(product=self.product_a)

        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={
            analytic_account_company_a.id: 50,
            inter_company_analytic_account.id: 50,
            f"{analytic_account_company_a.id},{inter_company_analytic_account.id}": 100
        })
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)

        self.assertEqual(supplier_invoice.invoice_line_ids.analytic_distribution, {str(inter_company_analytic_account.id): 50})

    def test_default_analytic_distribution_company_a(self):
        """
        [Analytic Distribution Model is set for Company A]
        - With Company A, create an Invoice for Company B with a line set with an analytic distribution model not available for Company B
        -> There should be no analytic distribution set on the supplier invoice line as there is no analytic distribution model available for Company B
        and the analytic account is not available for Company B
        """
        analytic_account_company_a = self._configure_analytic(company=self.company_a, product=self.product_a)

        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={analytic_account_company_a.id: 100})
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)

        self.assertFalse(supplier_invoice.invoice_line_ids.analytic_distribution, "Analytic distribution should not be set on the invoice line.")

    def test_inter_company_invoice_flow_sub_companies(self):
        """
        Test that the flow with inter company invoice is also working properly with sub companies
        """
        # Create branches for company a
        self.company_a.write({'child_ids': [
            Command.create({'name': 'Branch 1 of company a'}),
            Command.create({'name': 'Branch 2 of company a'}),
        ]})
        self.cr.precommit.run()  # load the COA

        branch_1, branch_2 = self.company_a.child_ids
        (branch_1 + branch_2).write({
            'intercompany_generate_bills_refund': True,
        })

        # It's required to have an intercompany_journal_id set to be able to do the generation
        for branch in [branch_1, branch_2]:
            branch.intercompany_purchase_journal_id = self.env['account.journal'].create({
                'name': 'Vendor Bills - Test',
                'code': 'TEXJ',
                'type': 'purchase',
                'company_id': branch.id,
            })

        # Select the two branches
        self.env.user.write({
            'company_ids': [Command.set((branch_1 + branch_2).ids)],
            'company_id': branch_1.id,
        })

        # Invoice from Branch 1 to Branch 2
        customer_invoice = self.env['account.move'].with_context(allowed_company_ids=branch_1.ids).create({
            'move_type': 'out_invoice',
            'invoice_date': '2023-05-01',
            'partner_id': branch_2.partner_id.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'quantity': 1.0,
                'tax_ids': False,
            })]
        })

        customer_invoice.action_post()
        bill = self.env['account.move'].search([('move_type', '=', 'in_invoice')], limit=1)

        self.assertRecordValues(bill, [{
            'partner_id': branch_1.partner_id.id,
            'company_id': branch_2.id,
            'payment_reference': customer_invoice.payment_reference,
        }])

    def test_inter_company_invoice_product_not_accessible(self):
        """
        Whenever Company A invoices Company B with a Product A defined only for Company A
        We don't set Product A (access error) but we define only the invoice line's label
        with Product A's name
        """
        self.product_a.company_id = self.company_a
        self._create_post_invoice(self.product_a.id)
        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)
        self.assertFalse(supplier_invoice.invoice_line_ids.product_id, "No product should be set")
        self.assertEqual(supplier_invoice.invoice_line_ids.name, self.product_a.name)

    def test_analytic_distribution_model_partner(self):
        """
        If company B defines Company A as a partner in its distribution model, the distribution should be retrieved
        """
        inter_company_analytic_account = self._configure_analytic(product=self.product_b)
        analytic_account_company_b = self._configure_analytic(company=self.company_b, partner=self.company_a.partner_id)
        self._create_post_invoice(product_id=self.product_a.id, analytic_distribution={inter_company_analytic_account.id: 100})

        supplier_invoice = self.env['account.move'].with_user(self.res_users_company_b).search([('move_type', '=', 'in_invoice')], limit=1)

        expected_distribution = {
            str(inter_company_analytic_account.id): 100,
            str(analytic_account_company_b.id): 100
        }
        self.assertEqual(supplier_invoice.invoice_line_ids.analytic_distribution, expected_distribution)

    def test_inter_company_attachment_with_contact_as_partner(self):
        """
        Test that when creating and printing an invoice in company A for an individual contact belonging to company B,
        the corresponding bill in company B there is an attachment.
        """
        company_partner = self.env['res.partner'].create({
            'name': 'company partner',
            'parent_id': self.company_b.partner_id.id,
        })

        customer_invoice = self.env['account.move'].create({
            'company_id': self.company_a.id,
            'move_type': 'out_invoice',
            'invoice_date': '2023-05-01',
            'partner_id': company_partner.id,
            'invoice_line_ids': [Command.create({
                'product_id': self.product_a.id,
                'price_unit': 100.0,
                'quantity': 1.0,
                'tax_ids': False,
            })]
        })

        customer_invoice.action_post()

        self.env['account.move.send.wizard'].with_context(active_model='account.move', active_ids=customer_invoice.id)._generate_and_send_invoices(customer_invoice)

        bill = self.env['account.move'].search([('move_type', '=', 'in_invoice'), ('company_id', '=', self.company_b.id)], limit=1)
        self.assertTrue(bill.attachment_ids)

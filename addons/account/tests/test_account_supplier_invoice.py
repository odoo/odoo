from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.exceptions import Warning

class TestAccountSupplierInvoice(AccountingTestCase):

    def test_supplier_invoice(self):
        tax = self.env['account.tax'].create({
            'name': 'Tax 10.0',
            'amount': 10.0,
            'amount_type': 'fixed',
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'test account',
        })

        # Should be changed by automatic on_change later
        invoice_account = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1).id
        invoice_line_account = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id)], limit=1).id

        invoice = self.env['account.invoice'].create({'partner_id': self.env.ref('base.res_partner_2').id,
            'account_id': invoice_account,
            'type': 'in_invoice',
        })

        self.env['account.invoice.line'].create({'product_id': self.env.ref('product.product_product_4').id,
            'quantity': 1.0,
            'price_unit': 100.0,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            'account_id': invoice_line_account,
            'invoice_line_tax_ids': [(6, 0, [tax.id])],
            'account_analytic_id': analytic_account.id,
        })

        # check that Initially supplier bill state is "Draft"
        self.assertTrue((invoice.state == 'draft'), "Initially vendor bill state is Draft")

        #change the state of invoice to open by clicking Validate button
        invoice.action_invoice_open()

        #I cancel the account move which is in posted state and verifies that it gives warning message
        with self.assertRaises(Warning):
            invoice.move_id.button_cancel()

    def test_supplier_invoice2(self):
        tax_fixed = self.env['account.tax'].create({
            'sequence': 10,
            'name': 'Tax 10.0 (Fixed)',
            'amount': 10.0,
            'amount_type': 'fixed',
            'include_base_amount': True,
        })
        tax_percent_included_base_incl = self.env['account.tax'].create({
            'sequence': 20,
            'name': 'Tax 50.0% (Percentage of Price Tax Included)',
            'amount': 50.0,
            'amount_type': 'division',
            'include_base_amount': True,
        })
        tax_percentage = self.env['account.tax'].create({
            'sequence': 30,
            'name': 'Tax 20.0% (Percentage of Price)',
            'amount': 20.0,
            'amount_type': 'percent',
            'include_base_amount': False,
        })
        analytic_account = self.env['account.analytic.account'].create({
            'name': 'test account',
        })

        # Should be changed by automatic on_change later
        invoice_account = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_receivable').id)], limit=1).id
        invoice_line_account = self.env['account.account'].search([('user_type_id', '=', self.env.ref('account.data_account_type_expenses').id)], limit=1).id

        invoice = self.env['account.invoice'].create({'partner_id': self.env.ref('base.res_partner_2').id,
            'account_id': invoice_account,
            'type': 'in_invoice',
        })

        invoice_line = self.env['account.invoice.line'].create({'product_id': self.env.ref('product.product_product_4').id,
            'quantity': 5.0,
            'price_unit': 100.0,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            'account_id': invoice_line_account,
            'invoice_line_tax_ids': [(6, 0, [tax_fixed.id, tax_percent_included_base_incl.id, tax_percentage.id])],
            'account_analytic_id': analytic_account.id,
        })
        invoice.compute_taxes()

        # check that Initially supplier bill state is "Draft"
        self.assertTrue((invoice.state == 'draft'), "Initially vendor bill state is Draft")

        #change the state of invoice to open by clicking Validate button
        invoice.action_invoice_open()

        # Check if amount and corresponded base is correct for all tax scenarios given on a computational base
        # Keep in mind that tax amount can be changed by the user at any time before validating (based on the invoice and tax laws applicable)
        invoice_tax = invoice.tax_line_ids.sorted(key=lambda r: r.sequence)
        self.assertEquals(invoice_tax.mapped('amount'), [50.0, 550.0, 220.0])
        self.assertEquals(invoice_tax.mapped('base'), [500.0, 550.0, 1100.0])

        #I cancel the account move which is in posted state and verifies that it gives warning message
        with self.assertRaises(Warning):
            invoice.move_id.button_cancel()

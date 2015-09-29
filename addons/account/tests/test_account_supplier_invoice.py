from openerp.addons.account.tests.account_test_classes import AccountingTestCase
from openerp.exceptions import Warning

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
        invoice.signal_workflow('invoice_open')

        #I cancel the account move which is in posted state and verifies that it gives warning message
        with self.assertRaises(Warning):
            invoice.move_id.button_cancel()

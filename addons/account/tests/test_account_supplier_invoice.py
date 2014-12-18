from openerp.addons.mail.tests.common import TestMail
from openerp.exceptions import Warning
from openerp.tools import float_compare

class TestAccountSupplierInvoice(TestMail):

    def setUp(self):
        super(TestAccountSupplierInvoice, self).setUp()

    def test_supplier_invoice(self):
        tax = self.env['account.tax'].create({
            'name': 'Tax 10.0',
            'amount': 10.0,
            'amount_type': 'fixed',
        })

        invoice = self.env['account.invoice'].create({'partner_id': self.env.ref('base.res_partner_2').id,
            'account_id': self.env.ref('account.a_recv').id,
            'type': 'in_invoice',
        })

        self.env['account.invoice.line'].create({'product_id': self.env.ref('product.product_product_4').id,
            'quantity': 1.0,
            'price_unit': 100.0,
            'invoice_id': invoice.id,
            'name': 'product that cost 100',
            'invoice_line_tax_id':[(6, 0, [tax.id])],
        })

        # check that Initially supplier invoice state is "Draft"
        self.assertTrue((invoice.state == 'draft'), "Initially supplier invoice state is Draft")

        #change the state of invoice to open by clicking Validate button
        invoice.signal_workflow('invoice_open')

        #I cancel the account move which is in posted state and verifies that it gives warning message
        with self.assertRaises(Warning):
            invoice.move_id.button_cancel()

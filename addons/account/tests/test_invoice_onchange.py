from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tests import tagged
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestInvoiceOnchange(AccountingTestCase):

    def setUp(self):
        super(TestInvoiceOnchange, self).setUp()
        self.invoice_line_onchange = self.env['account.invoice.line']._onchange_spec()
        self.half_currency = self.env['res.currency'].create({
            'name': 'HALF', 'symbol': '$HALF',
            'rate_ids': [(0, 0, {'name': '1980-01-01', 'rate': 2})],
        })
        self.apples_product = self.env['product.product'].create(dict(
            self.env['product.product'].default_get(self.env['product.product']._fields),
            lst_price=10, name='apples',
        ))

    def test_invoice_currency_onchange(self):
        self_ctx = self.env['account.invoice'].with_context(type='out_invoice')
        with Form(self_ctx, view='account.invoice_form') as invoice_form:
            invoice_form.partner_id = self.env.user.partner_id
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.product_id = self.apples_product
            # Check onchange keep price_unit if currency not changed
            self.assertEqual(invoice_line_form.price_unit, 10)
            invoice_form.currency_id = self.half_currency
            with invoice_form.invoice_line_ids.new() as invoice_line_form:
                invoice_line_form.product_id = self.apples_product
            # Check onchange gives converted price with custom currency
            self.assertEqual(invoice_line_form.price_unit, 20)

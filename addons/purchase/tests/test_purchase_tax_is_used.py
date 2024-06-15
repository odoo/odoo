from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class PurchaseTestTaxTotals(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.po_product = cls.env['product.product'].create({
            'name': 'Odoo course',
            'type': 'service',
        })

    def test_tax_is_used_when_in_transactions(self):
        ''' Ensures that a tax is set to used when it is part of some transactions '''

        # Account.move is one type of transaction
        tax_purchase = self.env['account.tax'].create({
            'name': 'test_is_used_purchase',
            'amount': '100',
        })

        self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'order_line': [
                Command.create({
                    'name': 'order_line',
                    'product_id': self.po_product.id,
                    'product_qty': 1.0,
                    'price_unit': 100.0,
                    'taxes_id': [Command.set(tax_purchase.ids)],
                }),
            ],
        })
        tax_purchase.invalidate_model(fnames=['is_used'])
        self.assertTrue(tax_purchase.is_used)

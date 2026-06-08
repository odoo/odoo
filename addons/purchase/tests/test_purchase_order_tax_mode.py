from odoo.addons.account.tests.test_account_move_tax_mode import TestDocumentTaxModeCommon
from odoo import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestPurchaseOrderTaxMode(TestDocumentTaxModeCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.tax_10_override_include.write({'type_tax_use': 'purchase'})
        cls.tax_10_override_exclude.write({'type_tax_use': 'purchase'})
        cls.tax_10_default.write({'type_tax_use': 'purchase'})
        cls.tax_20_default.write({'type_tax_use': 'purchase'})

        cls.test_product_a.supplier_taxes_id = cls.tax_10_default
        cls.purchase_order_one_line_with_product = cls.env['purchase.order'].create([{
            'partner_id': cls.partner_a.id,
            'order_line': [
                Command.create({'product_id': cls.test_product_a.id}),
            ],
        }])

    def test_purchase_order_tax_mode_change_with_product(self):
        purchase_order = self.purchase_order_one_line_with_product
        self._test_tax_mode_change_with_product(purchase_order, 'purchase_order')

    def test_purchase_order_tax_mode_change_with_product_with_tax_override_taxes_company_tax_excluded(self):
        purchase_order = self.purchase_order_one_line_with_product
        self._test_tax_mode_change_with_product_with_tax_override_taxes_company_tax_excluded(purchase_order, 'purchase_order')

    def test_purchase_order_tax_mode_change_with_product_with_tax_override_taxes_company_tax_included(self):
        self.env.company.account_price_include = 'tax_included'
        purchase_order = self.env['purchase.order'].create([{
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.test_product_b.id})],
        }])
        self._test_tax_mode_change_with_product_with_tax_override_taxes_company_tax_included(purchase_order, 'purchase_order')

    def test_purchase_order_tax_mode_change_with_product_with_mixed_taxes_company_tax_excluded(self):
        purchase_order = self.purchase_order_one_line_with_product
        self._test_tax_mode_change_with_product_with_mixed_taxes_company_tax_excluded(purchase_order, 'purchase_order')

    def test_purchase_order_tax_mode_change_with_product_with_mixed_taxes_company_tax_included(self):
        self.env.company.account_price_include = 'tax_included'
        purchase_order = self.env['purchase.order'].create([{
            'partner_id': self.partner_a.id,
            'order_line': [Command.create({'product_id': self.test_product_b.id})],
        }])
        self._test_tax_mode_change_with_product_with_mixed_taxes_company_tax_included(purchase_order, 'purchase_order')

    def test_purchase_order_tax_mode_change_manual_price_unit_with_product(self):
        purchase_order = self.purchase_order_one_line_with_product
        self._test_tax_mode_change_manual_price_unit_with_product(purchase_order, 'purchase_order')

    def test_purchase_order_tax_mode_change_add_tax_manual_price_unit_with_product(self):
        purchase_order = self.purchase_order_one_line_with_product
        self._test_tax_mode_change_add_tax_manual_price_unit_with_product(purchase_order, 'purchase_order')

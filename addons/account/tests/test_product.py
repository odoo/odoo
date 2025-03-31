# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestProduct(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.internal_user = new_test_user(
            cls.env,
            login="internal_user",
            groups="base.group_user",
        )
        cls.account_manager_user = new_test_user(
            cls.env,
            login="account_manager_user",
            groups="account.group_account_manager",
        )

    def test_internal_user_can_read_product_with_tax_and_tags(self):
        """Internal users need read access to products, no matter their taxes."""
        # Add a tag to product_a's default tax
        tax_line_tag = self.env["account.account.tag"].create({
            "name": "Tax tag",
            "applicability": "taxes",
        })
        self.product_a.taxes_id.repartition_line_ids.tag_ids = tax_line_tag
        # Check that internal user can read product_a
        self.env.invalidate_all()
        with Form(self.product_a.with_user(self.internal_user)) as form_a:
            # The tax string itself is not very important here; we just check
            # it has a value and we can read it, so there were no access errors
            self.assertTrue(form_a.tax_string)

    def test_multi_company_product_tax(self):
        """ Ensure default taxes are set for all companies on products with no company set. """
        product_without_company = self.env['product.template'].with_context(allowed_company_ids=self.env.company.ids).create({
            'name': 'Product Without a Company',
        })
        product_with_company = self.env['product.template'].with_context(allowed_company_ids=self.env.company.ids).create({
            'name': 'Product With a Company',
            'company_id': self.company_data['company'].id,
        })
        companies = self.env['res.company'].sudo().search([])
        # Product should have all the default taxes of the other companies.
        self.assertRecordValues(product_without_company.sudo(), [{
            'taxes_id': companies.account_sale_tax_id.ids,
            'supplier_taxes_id': companies.account_purchase_tax_id.ids,
        }])  # Take care that inactive default taxes won't be shown on the product
        # Product should have only the default tax of the company it belongs to.
        self.assertRecordValues(product_with_company.sudo(), [{
            'taxes_id': self.company_data['company'].account_sale_tax_id.ids,
            'supplier_taxes_id': self.company_data['company'].account_purchase_tax_id.ids,
        }])

    def test_account_manager_user_can_create_product(self):
        """Test that a user with group_account_manager can create a product."""
        product = self.env['product.product'].with_user(self.account_manager_user).create({
            'name': 'Test Accountant', 'type': 'consu', 'list_price': 50.0,
        })
        self.assertTrue(product)

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

    def test_product_tax_with_company_and_branch(self):
        """Ensure that setting a tax on a product overrides the default tax of branch companies.
            as branches share taxes with their parent company."""
        parent_company = self.env.company
        # Create a branch company and set a default sales tax.
        self.env['res.company'].create({
            'name': 'Branch Company',
            'parent_id': parent_company.id,
            'account_sale_tax_id': parent_company.account_sale_tax_id.id,
        })

        tax_new = self.env['account.tax'].create({
            'name': "tax_new",
            'amount_type': 'percent',
            'amount': 21.0,
            'type_tax_use': 'sale',
        })

        # Create a product in the parent company and set its sales tax to the new tax
        product = self.env['product.template'].with_context(allowed_company_ids=[parent_company.id]).create({
            'name': 'Product with new Tax',
            'taxes_id': tax_new.ids,
        })

        self.assertEqual(product.taxes_id, tax_new, "The branch company default tax shouldn't be set if we set a different tax on the product from the parent company.")

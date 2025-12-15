# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.sale_management.tests.common import SaleManagementCommon


@tagged('-at_install', 'post_install')
class TestSaleOrderTemplate(SaleManagementCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.branch_company, cls.other_company = cls.env['res.company'].create([
            {
                'name': "Branch company",
                'parent_id': cls.company.id,
            },
            {'name': "Other Company"},
        ])
        (
            cls.parent_company_product,
            cls.branch_company_product,
            cls.other_company_product,
        ) = cls.env['product.product'].create([
            {
                'name': 'Parent company product',
                'company_id': cls.company.id,
            },
            {
                'name': 'Branch company product',
                'company_id': cls.branch_company.id,
            },
            {
                'name': 'Other company product',
                'company_id': cls.other_company.id,
            },
        ])

    def test_no_restricted_product_on_shared_template(self):
        self.empty_order_template.company_id = False

        with self.assertRaises(UserError):
            self.empty_order_template.sale_order_template_line_ids = [
                Command.create({
                    'product_id': self.parent_company_product.id,
                }),
            ]

    def test_template_cannot_use_unrelated_company_products(self):
        # Access to products of other companies
        with self.assertRaises(UserError):
            self.empty_order_template.sale_order_template_line_ids = [
                Command.create({
                    'product_id': self.other_company_product.id,
                }),
            ]

    def test_parent_template_cannot_use_branch_company_products(self):
        with self.assertRaises(UserError):
            self.empty_order_template.sale_order_template_line_ids = [
                Command.create({
                    'product_id': self.branch_company_product.id,
                }),
            ]

    def test_branch_template_can_use_parent_company_products(self):
        self.assertFalse(self.product.company_id)
        self.empty_order_template.company_id = self.branch_company.id

        self.empty_order_template.write({
            'sale_order_template_line_ids': [
                Command.create({
                    'product_id': self.branch_company_product.id,
                }),
                Command.create({
                    'product_id': self.parent_company_product.id,
                }),
                Command.create({  # Shared product
                    'product_id': self.product.id,
                }),
            ],
        })

    def test_company_changes_on_template(self):
        """Test `_check_company_id` constraint.

        Since most multi-company issues are already catched by the automated `check_company` logic
        (see other tests), we have to trigger issues the other way (through the template field) to
        test the constraint.
        """
        self.empty_order_template.write({
            'company_id': self.company.id,
            'sale_order_template_line_ids': [
                Command.create({
                    'product_id': self.parent_company_product.id,
                })
            ],
        })

        # Branch company is allowed to use parent company products
        self.empty_order_template.company_id = self.branch_company.id

        # Cannot share template if contains restricted products
        with self.assertRaises(ValidationError):
            self.empty_order_template.company_id = False

        # Template cannot hold products from other companies
        with self.assertRaises(ValidationError):
            self.empty_order_template.company_id = self.other_company.id

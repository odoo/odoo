# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import Form, tagged
from odoo.tests.common import new_test_user
from odoo import Command


@tagged('post_install', 'post_install_l10n', '-at_install')
class TestProduct(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref)
        cls.internal_user = new_test_user(
            cls.env, login="internal_user", groups="base.group_user"
        )

    def test_internal_user_can_read_product_with_tax_and_tags(self):
        """Internal users need read access to products, no matter their taxes."""
        # Add a tag to product_a's default tax
        self.company_data["company"].country_id = self.env.ref("base.us")
        tax_line_tag = self.env["account.account.tag"].create(
            {
                "name": "Tax tag",
                "applicability": "taxes",
                "country_id": self.company_data["company"].country_id.id,
            }
        )
        repartition_lines = (
            self.product_a.taxes_id.invoice_repartition_line_ids
            | self.product_a.taxes_id.refund_repartition_line_ids
        ).filtered_domain([("repartition_type", "=", "tax")])
        repartition_lines.write({"tag_ids": [Command.link(tax_line_tag.id)]})
        # Check that internal user can read product_a
        with Form(
            self.product_a.with_user(self.internal_user).with_context(lang="en_US")
        ) as form_a:
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

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestSaleOnchanges(TransactionCase):

    def test_sale_warnings(self):
        """Test warnings & SO/SOL updates when partner/products with sale warnings are used."""
        partner_with_warning = self.env['res.partner'].create({
            'name': 'Test', 'sale_warn': 'warning', 'sale_warn_msg': 'Highly infectious disease'})
        partner_with_block_warning = self.env['res.partner'].create({
            'name': 'Test2', 'sale_warn': 'block', 'sale_warn_msg': 'Cannot afford our services'})

        sale_order = self.env['sale.order'].create({'partner_id': partner_with_warning.id})
        warning = sale_order._onchange_partner_id_warning()
        self.assertDictEqual(warning, {
            'warning': {
                'title': "Warning for Test",
                'message': partner_with_warning.sale_warn_msg,
            },
        })

        sale_order.partner_id = partner_with_block_warning
        warning = sale_order._onchange_partner_id_warning()
        self.assertDictEqual(warning, {
            'warning': {
                'title': "Warning for Test2",
                'message': partner_with_block_warning.sale_warn_msg,
            },
        })

        # Verify partner-related fields have been correctly reset
        self.assertFalse(sale_order.partner_id.id)
        self.assertFalse(sale_order.partner_invoice_id.id)
        self.assertFalse(sale_order.partner_shipping_id.id)
        self.assertFalse(sale_order.pricelist_id.id)

        # Reuse non blocking partner for product warning tests
        sale_order.partner_id = partner_with_warning
        product_with_warning = self.env['product.product'].create({
            'name': 'Test Product', 'sale_line_warn': 'warning', 'sale_line_warn_msg': 'Highly corrosive'})
        product_with_block_warning = self.env['product.product'].create({
            'name': 'Test Product (2)', 'sale_line_warn': 'block', 'sale_line_warn_msg': 'Not produced anymore'})

        sale_order_line = self.env['sale.order.line'].create({
            'order_id': sale_order.id,
            'product_id': product_with_warning.id,
        })
        warning = sale_order_line._onchange_product_id_warning()
        self.assertDictEqual(warning, {
            'warning': {
                'title': "Warning for Test Product",
                'message': product_with_warning.sale_line_warn_msg,
            },
        })

        sale_order_line.product_id = product_with_block_warning
        warning = sale_order_line._onchange_product_id_warning()

        self.assertDictEqual(warning, {
            'warning': {
                'title': "Warning for Test Product (2)",
                'message': product_with_block_warning.sale_line_warn_msg,
            },
        })

        self.assertFalse(sale_order_line.product_id.id)

    def test_create_products_in_different_companies(self):
        """ Ensures the product's constrain on `company_id` doesn't block the creation of multiple
        products in different companies (see `product.template` `_check_sale_product_company`.)
        """
        company_a = self.env['res.company'].create({'name': 'Company A'})
        company_b = self.env['res.company'].create({'name': 'Company B'})
        products = self.env['product.template'].create([
            {'name': "Product Test 1", 'company_id': company_a.id},
            {'name': "Product Test 2", 'company_id': company_b.id},
            {'name': "Product Test 3", 'company_id': False},
        ])
        self.assertRecordValues(products, [
            {'company_id': company_a.id},
            {'company_id': company_b.id},
            {'company_id': False},
        ])

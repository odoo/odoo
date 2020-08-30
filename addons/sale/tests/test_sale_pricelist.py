# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestSaleCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestSaleOrder(TestSaleCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        Pricelist = cls.env['product.pricelist']
        PricelistItem = cls.env['product.pricelist.item']
        SaleOrder = cls.env['sale.order'].with_context(tracking_disable=True)
        SaleOrderLine = cls.env['sale.order.line'].with_context(tracking_disable=True)

        # Create a product category
        cls.product_category_1 = cls.env['product.category'].create({
            'name': 'Product Category for pricelist',
        })
        # Create a pricelist with discount policy: percentage on services, fixed price for product_order
        cls.pricelist_discount_incl = Pricelist.create({
            'name': 'Pricelist A',
            'discount_policy': 'with_discount',
            'company_id': cls.company_data['company'].id,
        })
        PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_incl.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.company_data['product_service_order'].product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 10
        })
        PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_incl.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.company_data['product_service_delivery'].product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 20,
        })
        cls.pricelist_discount_incl_item3 = PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_incl.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.company_data['product_order_no'].product_tmpl_id.id,
            'compute_price': 'fixed',
            'fixed_price': 211,
        })

        # Create a pricelist without discount policy: formula for product_category_1 category, percentage for service_order
        cls.pricelist_discount_excl = Pricelist.create({
            'name': 'Pricelist B',
            'discount_policy': 'without_discount',
            'company_id': cls.company_data['company'].id,
        })
        PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_excl.id,
            'applied_on': '2_product_category',
            'categ_id': cls.product_category_1.id,
            'compute_price': 'formula',
            'base': 'standard_price',
            'price_discount': 10,
        })
        PricelistItem.create({
            'pricelist_id': cls.pricelist_discount_excl.id,
            'applied_on': '1_product',
            'product_tmpl_id': cls.company_data['product_service_order'].product_tmpl_id.id,
            'compute_price': 'percentage',
            'percent_price': 20,
        })

        # create a generic Sale Order with all classical products and empty pricelist
        cls.sale_order = SaleOrder.create({
            'partner_id': cls.partner_a.id,
            'partner_invoice_id': cls.partner_a.id,
            'partner_shipping_id': cls.partner_a.id,
            'pricelist_id': cls.company_data['default_pricelist'].id,
        })
        cls.sol_product_order = SaleOrderLine.create({
            'name': cls.company_data['product_order_no'].name,
            'product_id': cls.company_data['product_order_no'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_order_no'].uom_id.id,
            'price_unit': cls.company_data['product_order_no'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_deliver = SaleOrderLine.create({
            'name': cls.company_data['product_service_delivery'].name,
            'product_id': cls.company_data['product_service_delivery'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_service_delivery'].uom_id.id,
            'price_unit': cls.company_data['product_service_delivery'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_serv_order = SaleOrderLine.create({
            'name': cls.company_data['product_service_order'].name,
            'product_id': cls.company_data['product_service_order'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_service_order'].uom_id.id,
            'price_unit': cls.company_data['product_service_order'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })
        cls.sol_prod_deliver = SaleOrderLine.create({
            'name': cls.company_data['product_delivery_no'].name,
            'product_id': cls.company_data['product_delivery_no'].id,
            'product_uom_qty': 2,
            'product_uom': cls.company_data['product_delivery_no'].uom_id.id,
            'price_unit': cls.company_data['product_delivery_no'].list_price,
            'order_id': cls.sale_order.id,
            'tax_id': False,
        })

    def test_sale_with_pricelist_discount_included(self):
        """ Test SO with the pricelist and check unit price appeared on its lines """
        # Change the pricelist
        self.sale_order.write({'pricelist_id': self.pricelist_discount_incl.id})
        # Trigger onchange to reset discount, unit price, subtotal, ...
        for line in self.sale_order.order_line:
            line.product_id_change()
            line._onchange_discount()
        # Check that pricelist of the SO has been applied on the sale order lines or not
        for line in self.sale_order.order_line:
            if line.product_id == self.company_data['product_order_no']:
                self.assertEqual(line.price_unit, self.pricelist_discount_incl_item3.fixed_price, 'Price of product_order should be %s applied on the order line' % (self.pricelist_discount_incl_item3.fixed_price,))
            else:  # only services (service_order and service_deliver)
                for item in self.sale_order.pricelist_id.item_ids.filtered(lambda l: l.product_tmpl_id == line.product_id.product_tmpl_id):
                    price = item.percent_price
                    self.assertEqual(price, (line.product_id.list_price - line.price_unit) / line.product_id.list_price * 100, 'Pricelist of the SO should be applied on an order line %s' % (line.product_id.name,))

    def test_sale_with_pricelist_discount_excluded(self):
        """ Test SO with the pricelist 'discount displayed' and check discount and unit price appeared on its lines """
        # Add group 'Discount on Lines' to the user
        self.env.user.write({'groups_id': [(4, self.env.ref('product.group_discount_per_so_line').id)]})

        # Set product category on consumable products (for the pricelist item applying on this category)
        self.company_data['product_order_no'].write({'categ_id': self.product_category_1.id})
        self.company_data['product_delivery_no'].write({'categ_id': self.product_category_1.id})

        # Change the pricelist
        self.sale_order.write({'pricelist_id': self.pricelist_discount_excl.id})
        # Trigger onchange to reset discount, unit price, subtotal, ...
        for line in self.sale_order.order_line:
            line.product_id_change()
            line._onchange_discount()

        # Check pricelist of the SO apply or not on order lines where pricelist contains formula that add 15% on the cost price
        for line in self.sale_order.order_line:
            if line.product_id.categ_id in self.sale_order.pricelist_id.item_ids.mapped('categ_id'):  # reduction per category (consummable only)
                for item in self.sale_order.pricelist_id.item_ids.filtered(lambda l: l.categ_id == line.product_id.categ_id):
                    self.assertEqual(line.discount, item.price_discount, "Discount should be displayed on order line %s since its category get some discount" % (line.name,))
                self.assertEqual(line.price_unit, line.product_id.standard_price, "Price unit should be the cost price for product %s" % (line.name,))
            else:
                if line.product_id == self.company_data['product_service_order']:  # reduction for this product
                    self.assertEqual(line.discount, 20.0, "Discount for product %s should be 20 percent with pricelist %s" % (line.name, self.pricelist_discount_excl.name))
                    self.assertEqual(line.price_unit, line.product_id.list_price, 'Unit price of order line should be a sale price as the pricelist not applied on the other category\'s product')
                else:  # no discount for the rest
                    self.assertEqual(line.discount, 0.0, 'Pricelist of SO should not be applied on an order line')
                    self.assertEqual(line.price_unit, line.product_id.list_price, 'Unit price of order line should be a sale price as the pricelist not applied on the other category\'s product')

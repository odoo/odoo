# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, tagged

from odoo.addons.sale_management.tests.common import SaleManagementCommon


@tagged('-at_install', 'post_install')
class TestSaleOrder(SaleManagementCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # some variables to ease asserts in tests
        cls.pub_product_price = 100.0
        cls.pl_product_price = 80.0
        cls.tpl_discount = 10.0
        cls.pl_discount = (cls.pub_product_price - cls.pl_product_price) * 100 / cls.pub_product_price
        cls.merged_discount = 100.0 - (100.0 - cls.pl_discount) * (100.0 - cls.tpl_discount) / 100.0

        cls.pub_option_price = 200.0
        cls.pl_option_price = 100.0
        cls.tpl_option_discount = 20.0
        cls.pl_option_discount = (cls.pub_option_price - cls.pl_option_price) * 100 / cls.pub_option_price
        cls.merged_option_discount = 100.0 - (100.0 - cls.pl_option_discount) * (100.0 - cls.tpl_option_discount) / 100.0

        # create some products
        cls.product_1, cls.optional_product = cls.env['product.product'].create([
            {
                'name': 'Product 1',
                'lst_price': cls.pub_product_price,
            }, {
                'name': 'Optional product',
                'lst_price': cls.pub_option_price,
            }
        ])

        # create some quotation templates
        cls.quotation_template_no_discount = cls.env['sale.order.template'].create({
            'name': 'A quotation template',
            'sale_order_template_line_ids': [
                Command.create({
                    'product_id': cls.product_1.id,
                }),
            ],
            'sale_order_template_option_ids': [
                Command.create({
                    'product_id': cls.optional_product.id,
                }),
            ],
        })

        # create two pricelist with different discount policies (same total price)
        pricelist_rule_values = [
            Command.create({
                'name': 'Product 1 premium price',
                'applied_on': '1_product',
                'product_tmpl_id': cls.product_1.product_tmpl_id.id,
                'compute_price': 'fixed',
                'fixed_price': cls.pl_product_price,
            }),
            Command.create({
                'name': 'Optional product premium price',
                'applied_on': '1_product',
                'product_tmpl_id': cls.optional_product.product_tmpl_id.id,
                'compute_price': 'fixed',
                'fixed_price': cls.pl_option_price,
            }),
        ]

        (
            cls.discount_included_price_list,
            cls.discount_excluded_price_list
        ) = cls.env['product.pricelist'].create([
            {
                'name': 'Discount included Pricelist',
                'discount_policy': 'with_discount',
                'item_ids': pricelist_rule_values,
            }, {
                'name': 'Discount excluded Pricelist',
                'discount_policy': 'without_discount',
                'item_ids': pricelist_rule_values,
            }
        ])

        # variable kept to reduce code diff
        cls.sale_order = cls.empty_order

    def test_01_template_without_pricelist(self):
        """
        This test checks that without any rule in the pricelist, the public price
        of the product is used in the sale order after selecting a
        quotation template.
        """
        # first case, without discount in the quotation template
        self.sale_order.write({
            'sale_order_template_id': self.quotation_template_no_discount.id
        })
        self.sale_order._onchange_sale_order_template_id()

        self.assertEqual(
            len(self.sale_order.order_line),
            1,
            "The sale order shall contains the same number of products as"
            "the quotation template.")

        self.assertEqual(
            self.sale_order.order_line[0].product_id.id,
            self.product_1.id,
            "The sale order shall contains the same products as the"
            "quotation template.")

        self.assertEqual(
            self.sale_order.order_line[0].price_unit,
            self.pub_product_price,
            "Without any price list and discount, the public price of"
            "the product shall be used.")

        self.assertEqual(
            len(self.sale_order.sale_order_option_ids),
            1,
            "The sale order shall contains the same number of optional products as"
            "the quotation template.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].product_id.id,
            self.optional_product.id,
            "The sale order shall contains the same optional products as the"
            "quotation template.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pub_option_price,
            "Without any price list and discount, the public price of"
            "the optional product shall be used.")

        # add the option to the order
        self.sale_order.sale_order_option_ids[0].button_add_to_order()

        self.assertEqual(
            len(self.sale_order.order_line),
            2,
            "When an option is added, a new order line is created")

        self.assertEqual(
            self.sale_order.order_line[1].product_id.id,
            self.optional_product.id,
            "The sale order shall contains the same products as the"
            "quotation template.")

        self.assertEqual(
            self.sale_order.order_line[1].price_unit,
            self.pub_option_price,
            "Without any price list and discount, the public price of"
            "the optional product shall be used.")

    def test_02_template_with_discount_included_pricelist(self):
        """
        This test checks that with a 'discount included' price list,
        the price used in the sale order is computed according to the
        price list.
        """

        # first case, without discount in the quotation template
        self.sale_order.write({
            'pricelist_id': self.discount_included_price_list.id,
            'sale_order_template_id': self.quotation_template_no_discount.id
        })
        self.sale_order._onchange_sale_order_template_id()

        self.assertEqual(
            self.sale_order.order_line[0].price_unit,
            self.pl_product_price,
            "If a pricelist is set, the product price shall be computed"
            "according to it.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pl_option_price,
            "If a pricelist is set, the optional product price shall"
            "be computed according to it.")

        # add the option to the order
        self.sale_order.sale_order_option_ids[0].button_add_to_order()

        self.assertEqual(
            self.sale_order.order_line[1].price_unit,
            self.pl_option_price,
            "If a pricelist is set, the optional product price shall"
            "be computed according to it.")

    def test_03_template_with_discount_excluded_pricelist(self):
        """
        This test checks that with a 'discount excluded' price list,
        the price used in the sale order is the product public price and
        the discount is computed according to the price list.
        """
        self.sale_order.write({
            'pricelist_id': self.discount_excluded_price_list.id,
            'sale_order_template_id': self.quotation_template_no_discount.id
        })
        self.sale_order._onchange_sale_order_template_id()

        self.assertEqual(
            self.sale_order.order_line[0].price_unit,
            self.pub_product_price,
            "If a pricelist is set without discount included, the unit "
            "price shall be the public product price.")

        self.assertEqual(
            self.sale_order.order_line[0].price_subtotal,
            self.pl_product_price,
            "If a pricelist is set without discount included, the subtotal "
            "price shall be the price computed according to the price list.")

        self.assertEqual(
            self.sale_order.order_line[0].discount,
            self.pl_discount,
            "If a pricelist is set without discount included, the discount "
            "shall be computed according to the price unit and the subtotal."
            "price")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pub_option_price,
            "If a pricelist is set without discount included, the unit "
            "price shall be the public optional product price.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].discount,
            self.pl_option_discount,
            "If a pricelist is set without discount included, the discount "
            "shall be computed according to the optional price unit and"
            "the subtotal price.")

        # add the option to the order
        self.sale_order.sale_order_option_ids[0].button_add_to_order()

        self.assertEqual(
            self.sale_order.order_line[1].price_unit,
            self.pub_option_price,
            "If a pricelist is set without discount included, the unit "
            "price shall be the public optional product price.")

        self.assertEqual(
            self.sale_order.order_line[1].price_subtotal,
            self.pl_option_price,
            "If a pricelist is set without discount included, the subtotal "
            "price shall be the price computed according to the price list.")

        self.assertEqual(
            self.sale_order.order_line[1].discount,
            self.pl_option_discount,
            "If a pricelist is set without discount included, the discount "
            "shall be computed according to the price unit and the subtotal."
            "price")

    def test_04_update_pricelist_option_line(self):
        """
        This test checks that option line's values are correctly
        updated after a pricelist update
        """
        self.sale_order.write({
            'sale_order_template_id': self.quotation_template_no_discount.id
        })
        self.sale_order._onchange_sale_order_template_id()

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pub_option_price,
            "If no pricelist is set, the unit price shall be the option's product price.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].discount, 0,
            "If no pricelist is set, the discount should be 0.")

        self.sale_order.write({
            'pricelist_id': self.discount_included_price_list.id,
        })
        self.sale_order._recompute_prices()

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pl_option_price,
            "If a pricelist is set with discount included,"
            " the unit price shall be the option's product discounted price.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].discount, 0,
            "If a pricelist is set with discount included,"
            " the discount should be 0.")

        self.sale_order.write({
            'pricelist_id': self.discount_excluded_price_list.id,
        })
        self.sale_order._recompute_prices()

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].price_unit,
            self.pub_option_price,
            "If a pricelist is set without discount included,"
            " the unit price shall be the option's product sale price.")

        self.assertEqual(
            self.sale_order.sale_order_option_ids[0].discount,
            self.pl_option_discount,
            "If a pricelist is set without discount included,"
            " the discount should be correctly computed.")

    def test_option_creation(self):
        """Make sure the product uom is automatically added to the option when the product is specified"""
        order_form = Form(self.sale_order)
        with order_form.sale_order_option_ids.new() as option:
            option.product_id = self.product_1
        order = order_form.save()
        self.assertTrue(bool(order.sale_order_option_ids.uom_id))

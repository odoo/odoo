# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.sale_product_configurator.tests.common import TestProductConfiguratorCommon
from odoo.addons.base.tests.common import HttpCaseWithUserPortal, HttpCaseWithUserDemo


@tagged('post_install', '-at_install')
class TestWebsiteSaleProductConfigurator(TestProductConfiguratorCommon, HttpCaseWithUserPortal, HttpCaseWithUserDemo):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product_product_custo_desk.write({
            'optional_product_ids': [(4, cls.product_product_conf_chair.id)],
            'website_published': True,
        })
        cls.product_product_conf_chair.website_published = True

        ptav_ids = cls.product_product_custo_desk.attribute_line_ids.product_template_value_ids
        ptav_ids.filtered(lambda ptav: ptav.name == 'Aluminium').price_extra = 50.4

    def test_01_product_configurator_variant_price(self):
        product = self.product_product_conf_chair.with_user(self.user_portal)
        ptav_ids = self.product_product_custo_desk.attribute_line_ids.product_template_value_ids
        parent_combination = ptav_ids.filtered(lambda ptav: ptav.name in ('Aluminium', 'White'))
        self.assertEqual(product._is_add_to_cart_possible(parent_combination), True)
        # This is a regression test. The product configurator menu is proposed
        # whenever a product has optional products. However, as the end user
        # already picked a variant, the variant configuration menu is omitted
        # in this case. However, we still want to make sure that the correct
        # variant attributes are taken into account when calculating the price.
        url = self.product_product_custo_desk.website_url
        self.start_tour(url, 'website_sale_product_configurator_optional_products_tour', login='portal')

    def test_02_variants_modal_window(self):
        """
        The objective is to verify that the data concerning the variants are well transmitted
        even when passing through a modal window (product configurator).

        We create a product with the different attributes and we will modify them.
        If the information is not correctly transmitted,
        the default values of the variants will be used (the first one).
        """

        always_attribute, dynamic_attribute, never_attribute, never_attribute_custom = self.env['product.attribute'].create([
            {
                'name': 'Always attribute size',
                'display_type': 'radio',
                'create_variant': 'always'
            },
            {
                'name': 'Dynamic attribute size',
                'display_type': 'radio',
                'create_variant': 'dynamic'
            },
            {
                'name': 'Never attribute size',
                'display_type': 'radio',
                'create_variant': 'no_variant'
            },
            {
                'name': 'Never attribute size custom',
                'display_type': 'radio',
                'create_variant': 'no_variant'
            }
        ])
        always_S, always_M, dynamic_S, dynamic_M, never_S, never_M, never_custom_no, never_custom_yes = self.env['product.attribute.value'].create([
            {
                'name': 'S always',
                'attribute_id': always_attribute.id,
            },
            {
                'name': 'M always',
                'attribute_id': always_attribute.id,
            },
            {
                'name': 'S dynamic',
                'attribute_id': dynamic_attribute.id,
            },
            {
                'name': 'M dynamic',
                'attribute_id': dynamic_attribute.id,
            },
            {
                'name': 'S never',
                'attribute_id': never_attribute.id,
            },
            {
                'name': 'M never',
                'attribute_id': never_attribute.id,
            },
            {
                'name': 'No never custom',
                'attribute_id': never_attribute_custom.id,
            },
            {
                'name': 'Yes never custom',
                'attribute_id': never_attribute_custom.id,
                'is_custom': True,
            }
        ])

        product_short = self.env['product.template'].create({
            'name': 'Short (TEST)',
            'website_published': True,
        })

        self.env['product.template.attribute.line'].create([
            {
                'product_tmpl_id': product_short.id,
                'attribute_id': always_attribute.id,
                'value_ids': [(4, always_S.id), (4, always_M.id)],
            },
            {
                'product_tmpl_id': product_short.id,
                'attribute_id': dynamic_attribute.id,
                'value_ids': [(4, dynamic_S.id), (4, dynamic_M.id)],
            },
            {
                'product_tmpl_id': product_short.id,
                'attribute_id': never_attribute.id,
                'value_ids': [(4, never_S.id), (4, never_M.id)],
            },
            {
                'product_tmpl_id': product_short.id,
                'attribute_id': never_attribute_custom.id,
                'value_ids': [(4, never_custom_no.id), (4, never_custom_yes.id)],
            },
        ])

        # Add an optional product to trigger the modal window
        optional_product = self.env['product.template'].create({
            'name': 'Optional product (TEST)',
            'website_published': True,
        })
        product_short.optional_product_ids = [(4, optional_product.id)]

        old_sale_order = self.env['sale.order'].search([])
        self.start_tour("/", 'tour_variants_modal_window', login="demo")

        # Check the name of the created sale order line
        new_sale_order = self.env['sale.order'].search([]) - old_sale_order
        new_order_line = new_sale_order.order_line
        self.assertEqual(new_order_line.name, 'Short (TEST) (M always, M dynamic)\n\nNever attribute size: M never\nNever attribute size custom: Yes never custom: TEST')

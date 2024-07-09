# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.addons.sale.tests.product_configurator_common import TestProductConfiguratorCommon


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
        # Ensure that no pricelist is available during the test.
        # This ensures that tours with triggers on the amounts will run properly.
        self.env['product.pricelist'].search([]).action_archive()
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

    def test_product_configurator_force_dialog(self):
        """ Test that the product configurator is shown if forced. """
        self.env['website'].get_current_website().add_to_cart_action = 'force_dialog'
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
        })
        self.start_tour('/shop', 'website_sale_product_configurator_show_dialog')

    def test_product_configurator_optional_products(self):
        """ Test that the product configurator is shown if there are optional products. """
        optional_product = self.env['product.template'].create({
            'name': "Optional product",
            'website_published': True,
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        self.start_tour('/shop', 'website_sale_product_configurator_show_dialog')

    def test_product_configurator_single_variant(self):
        """ Test that the product configurator isn't shown if there's a single variant. """
        self.env.ref('website_sale.products_add_to_cart').active = True
        attribute = self.env['product.attribute'].create({
            'name': "Attribute",
            'value_ids': [Command.create({'name': "A"})],
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [Command.set(attribute.value_ids.ids)],
                }),
            ],
        })
        self.start_tour('/shop', 'website_sale_product_configurator_shop_hide_dialog')

    def test_product_configurator_on_product_page_empty_multi_checkbox(self):
        """ Test that the product configurator isn't shown if a product with a multi-checkbox
            attribute is added from the product page, even if no option was selected.
        """
        multi_attribute = self.env['product.attribute'].create({
            'name': "Multi-checkbox attribute",
            'display_type': 'multi',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': "A"}),
                Command.create({'name': "B"}),
            ],
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': multi_attribute.id,
                    'value_ids': [Command.set(multi_attribute.value_ids.ids)],
                }),
            ],
        })
        self.start_tour('/shop', 'website_sale_product_configurator_hide_dialog')

    def test_product_configurator_zero_priced(self):
        """ Test that zero-priced options can't be sold. """
        self.env['website'].get_current_website().prevent_zero_price_sale = True
        price_attribute = self.env['product.attribute'].create({
            'name': "Price",
            'value_ids': [
                Command.create({'name': "Zero-priced"}),
                Command.create({'name': "One-priced"}),
            ],
        })
        optional_product = self.env['product.template'].create({
            'name': "Optional product",
            'website_published': True,
            'list_price': 0,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': price_attribute.id,
                    'value_ids': [Command.set(price_attribute.value_ids.ids)],
                }),
            ],
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        optional_product.product_variant_ids[1].product_template_attribute_value_ids.price_extra = 1
        self.start_tour('/shop', 'website_sale_product_configurator_zero_priced')

    def test_product_configurator_with_taxes(self):
        """ Test that taxes are applied correctly. """
        self.env['website'].get_current_website().show_line_subtotals_tax_selection = 'tax_included'
        tax = self.env['account.tax'].create({'name': "Tax", 'amount': 10})
        optional_product = self.env['product.template'].create({
            'name': "Optional product",
            'website_published': True,
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'list_price': 100,
            'taxes_id': tax,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        self.start_tour('/shop', 'website_sale_product_configurator_taxes')

    def test_product_configurator_strikethrough_price(self):
        """ Test that the strikethrough price is applied correctly. """
        self.env['res.config.settings'].create({'group_product_price_comparison': True}).execute()
        optional_product = self.env['product.template'].create({
            'name': "Optional product",
            'website_published': True,
            'list_price': 5,
            'compare_list_price': 10,
        })
        main_product = self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'list_price': 100,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        self.env['website'].get_current_website().pricelist_id.write({
            'item_ids': [
                Command.create({
                    'applied_on': "1_product",
                    'fixed_price': 50,
                    'product_tmpl_id': main_product.id,
                }),
            ],
        })
        self.start_tour('/shop', 'website_sale_product_configurator_strikethrough_price')

    def test_product_configurator_sale_not_ok(self):
        """ Test that products which aren't `sale_ok` aren't displayed. """
        optional_product = self.env['product.template'].create({
            'name': "Optional product",
            'website_published': True,
            'sale_ok': False,
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        self.start_tour('/shop', 'website_sale_product_configurator_hide_dialog')

    def test_product_configurator_only_no_variant_attributes(self):
        """ Test that the product configurator is shown if a product with only no variant attributes
            is added from the shop page.
        """
        self.env.ref('website_sale.products_add_to_cart').active = True
        no_variant_attribute = self.env['product.attribute'].create({
            'name': "No variant attribute",
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': "A"}),
                Command.create({'name': "B"}),
            ],
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': no_variant_attribute.id,
                    'value_ids': [Command.set(no_variant_attribute.value_ids.ids)],
                })
            ],
        })
        self.start_tour("/shop", 'website_sale_product_configurator_shop_show_dialog')

    def test_product_configurator_only_dynamic_attributes(self):
        """ Test that the product configurator is shown if a product with only dynamic attributes is
            added from the shop page.
        """
        self.env.ref('website_sale.products_add_to_cart').active = True
        dynamic_attribute = self.env['product.attribute'].create({
            'name': "Dynamic attribute",
            'create_variant': 'dynamic',
            'value_ids': [
                Command.create({'name': "A"}),
                Command.create({'name': "B"}),
            ],
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': dynamic_attribute.id,
                    'value_ids': [Command.set(dynamic_attribute.value_ids.ids)],
                })
            ],
        })
        self.start_tour("/shop", 'website_sale_product_configurator_shop_show_dialog')

    def test_product_configurator_single_custom_attribute(self):
        """ Test that the product configurator is shown if a product with a single custom attribute
            is added from the shop page.
        """
        self.env.ref('website_sale.products_add_to_cart').active = True
        custom_attribute = self.env['product.attribute'].create({
            'name': "Custom attribute",
            'value_ids': [
                Command.create({
                    'name': "Custom value",
                    'is_custom': True,
                }),
            ],
        })
        self.env['product.template'].create({
            'name': "Main product",
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': custom_attribute.id,
                    'value_ids': [Command.set(custom_attribute.value_ids.ids)],
                })
            ],
        })
        self.start_tour("/shop", 'website_sale_product_configurator_shop_show_dialog')

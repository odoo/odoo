# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.addons.sale.tests.product_configurator_common import TestProductConfiguratorCommon
from odoo.addons.website.tests.common import HttpCaseWithWebsiteUser


@tagged('post_install', '-at_install')
class TestCustomize(HttpCaseWithUserDemo, HttpCaseWithUserPortal, TestProductConfiguratorCommon, HttpCaseWithWebsiteUser):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')

        product_attribute = cls.env['product.attribute'].create({
            'name': 'Legs',
            'visibility': 'visible',
            'sequence': 10,
            'value_ids': [
                Command.create({
                    'name': 'Steel - Test',
                    'sequence': 1,
                }),
                Command.create({
                    'name': 'Aluminium',
                    'sequence': 2,
                }),
            ]
        })
        # create a template
        product_template = cls.env['product.template'].create({
            'name': 'Test Product',
            'is_published': True,
            'list_price': 750,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': product_attribute.id,
                    'value_ids': [Command.set(product_attribute.value_ids.ids)]
                })
            ],
        })

        tax = cls.env['account.tax'].create({'name': "Test tax", 'amount': 10})
        product_template.taxes_id = tax

        # set a different price on the variants to differentiate them
        product_template_attribute_values = cls.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', product_template.id),
        ])

        for ptav in product_template_attribute_values:
            if ptav.name == "Steel - Test":
                ptav.price_extra = 0
            else:
                ptav.price_extra = 50.4

        # Ensure that no pricelist is available during the test.
        # This ensures that tours which triggers on the amounts will run properly, and that the
        # currency will be the company currency.
        cls.env['product.pricelist'].action_archive()

    def test_01_admin_shop_custom_attribute_value_tour(self):
        self.env.user.write(
            {'group_ids': [Command.link(self.env.ref('product.group_product_pricelist').id)]}
        )
        self.env['product.pricelist'].create({
            'name': 'Custom pricelist (TEST)',
            'sequence': 4,
            'item_ids': [(0, 0, {
                'base': 'list_price',
                'applied_on': '1_product',
                'product_tmpl_id': self.product_product_custo_desk.id,
                'price_discount': 20,
                'min_quantity': 2,
                'compute_price': 'formula'
            })]
        })
        self.start_tour("/", 'a_shop_custom_attribute_value', login="admin")

    def test_02_admin_shop_custom_attribute_value_tour(self):
        # Make sure pricelist rule exist
        self.env['product.pricelist'].create({
            'name': 'Base Pricelist',
            'item_ids': [Command.create({
                'base': 'list_price',
                'applied_on': '1_product',
                'product_tmpl_id': self.product_product_custo_desk.id,
                'price_discount': 20,
                'min_quantity': 2,
                'compute_price': 'formula',
            })],
        })

        self.start_tour("/", 'shop_custom_attribute_value', login="admin")

    def test_03_public_tour_shop_dynamic_variants(self):
        """ The goal of this test is to make sure product variants with dynamic
        attributes can be created by the public user (when being added to cart).
        """
        product_attribute = self.env['product.attribute'].create({
            'name': "Dynamic Attribute",
            'create_variant': 'dynamic',
            'value_ids': [
                Command.create({'name': "Dynamic Value 1"}),
                Command.create({'name': "Dynamic Value 2"}),
            ]
        })

        # create the template
        product_template = self.env['product.template'].create({
            'name': 'Dynamic Product',
            'website_published': True,
            'list_price': 10,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': product_attribute.id,
                    'value_ids': [Command.set(product_attribute.value_ids.ids)]
                })
            ]
        })

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', product_template.id),
        ])

        for ptav in product_template_attribute_values:
            if ptav.name == "Dynamic Value 1":
                ptav.price_extra = 10
            else:
                # 0 to not bother with the pricelist of the public user
                ptav.price_extra = 0

        self.start_tour("/", 'tour_shop_dynamic_variants')

    def test_04_portal_tour_deleted_archived_variants(self):
        """The goal of this test is to make sure deleted and archived variants
        are shown as impossible combinations.

        Using "portal" to have various users in the tests.
        """

        # create the attribute
        product_attribute = self.env['product.attribute'].create({
            'name': "My Attribute",
            'create_variant': 'always',
            'value_ids': [
                Command.create({'name': "My Value 1"}),
                Command.create({'name': "My Value 2"}),
                Command.create({'name': "My Value 3"}),
            ],
        })

        # create the template
        product_template = self.env['product.template'].create({
            'name': 'Test Product 2',
            'is_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': product_attribute.id,
                    'value_ids': [Command.set(product_attribute.value_ids.ids)]
                }),
            ],
        })

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', product_template.id),
        ])

        product_template_attribute_values[0].price_extra = 10
        product_template_attribute_values[1].price_extra = 20
        product_template_attribute_values[2].price_extra = 30

        # archive first combination (first variant)
        product_template.product_variant_ids[0].active = False
        # delete second combination (which is now first variant since cache has been cleared)
        product_template.product_variant_ids[0].unlink()

        self.start_tour("/", 'tour_shop_deleted_archived_variants', login="portal")

    def test_05_demo_tour_no_variant_attribute(self):
        """The goal of this test is to make sure attributes no_variant are
        correctly added to cart.

        Using "demo" to have various users in the tests.
        """

        product_attribute_no_variant = self.env['product.attribute'].create({
            'name': "No Variant Attribute",
            'create_variant': 'no_variant',
            'value_ids': [Command.create({'name': "No Variant Value"})],
        })

        # create the template
        product_template = self.env['product.template'].create({
            'name': 'Test Product 3',
            'website_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': product_attribute_no_variant.id,
                    'value_ids': [Command.set(product_attribute_no_variant.value_ids.ids)]
                })
            ]
        })

        # set a price on the value
        product_template.attribute_line_ids.product_template_value_ids.price_extra = 10

        self.start_tour("/", 'tour_shop_no_variant_attribute', login="demo")

        sol = self.env['sale.order.line'].search([
            ('product_id', '=', product_template.product_variant_id.id)
        ])
        self.assertTrue(sol)
        self.assertEqual(
            sol.product_no_variant_attribute_value_ids,
            product_template.attribute_line_ids.product_template_value_ids
        )

    def test_07_editor_shop(self):
        self.env.user.write(
            {'group_ids': [Command.link(self.env.ref('product.group_product_pricelist').id)]}
        )
        self.env['product.pricelist'].create([
            {'name': 'Base Pricelist', 'selectable': True},
            {'name': 'Other Pricelist', 'selectable': True}
        ])
        self.start_tour("/", 'shop_editor', login="website_user")

    def test_08_portal_tour_archived_variant_multiple_attributes(self):
        """The goal of this test is to make sure that an archived variant with multiple
        attributes only disabled other options if only one is missing or all are selected.

        Using "portal" to have various users in the tests.
        """

        attributes = self.env['product.attribute'].create([
            {
                'name': 'Size',
                'value_ids': [
                    Command.create({'name': 'Large'}),
                    Command.create({'name': 'Small'}),
                ],
            },
            {
                'name': 'Color',
                'value_ids': [
                    Command.create({'name': 'White'}),
                    Command.create({'name': 'Black'}),
                ],
            },
            {
                'name': 'Brand',
                'value_ids': [
                    Command.create({'name': 'Brand A'}),
                    Command.create({'name': 'Brand B'}),
                ],
            },
        ])


        product_template = self.env['product.template'].create({
            'name': 'Test Product 2',
            'is_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [Command.set(attribute.value_ids.ids)],
                }) for attribute in attributes
            ],
        })

        # Archive (Small, Black, Brand B) variant
        combination_to_archive = product_template.attribute_line_ids.product_template_value_ids.filtered(
            lambda ptav: ptav.product_attribute_value_id.name in ('Small', 'Black', 'Brand B')
        )
        variant_to_archive = product_template._get_variant_for_combination(
            combination_to_archive
        )
        self.assertTrue(variant_to_archive)
        variant_to_archive.action_archive()
        self.assertFalse(variant_to_archive.active)

        self.start_tour("/", 'tour_shop_archived_variant_multi', login="portal")

    def test_09_pills_variant(self):
        """The goal of this test is to make sure that you can click anywhere on a pill
        and still trigger a variant change. The radio input be visually hidden.

        Using "portal" to have various users in the tests.
        """

        attribute_size = self.env['product.attribute'].create({
            'name': 'Size',
            'create_variant': 'always',
            'display_type': 'pills',
            'value_ids': [
                Command.create({'name': 'Large'}),
                Command.create({'name': 'Small'}),
            ],
        })

        self.env['product.template'].create({
            'name': 'Test Product 2',
            'is_published': True,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute_size.id,
                    'value_ids': [Command.set(attribute_size.value_ids.ids)],
                })
            ],
        })

        self.start_tour("/", 'test_09_pills_variant', login="portal")

    def test_10_multi_checkbox_attribute(self):
        attribute = self.env['product.attribute'].create([
            {
                'name': 'Options',
                'create_variant': 'no_variant',
                'display_type': 'multi',
                'value_ids': [
                    Command.create({
                        'name': 'Option 1',
                        'default_extra_price': 1,
                        'sequence': 1,
                    }),
                    Command.create({
                        'name': 'Option 2',
                        'sequence': 2,
                    }),
                    Command.create({
                        'name': 'Option 3',
                        'default_extra_price': 3,
                        'sequence': 3,
                    }),
                    Command.create({
                        'name': 'Option 4',
                        'sequence': 4,
                    }),
                ],
            },
        ])
        product_template = self.env['product.template'].create({
            'name': 'Product Multi',
            'is_published': True,
            'list_price': 750,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [Command.set(attribute.value_ids.ids)],
                }),
            ],
        })
        # set an extra price for free attribute values on the product (nothing is free)
        self.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', product_template.id),
            ('price_extra', '=', 0),
        ]).price_extra = 2
        # set an exclusion between option 1 and option 3
        self.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', product_template.id),
            ('price_extra', '=', 1),
        ]).exclude_for = [
            Command.create({
                'product_tmpl_id': product_template.id,
                'value_ids': [Command.set(
                    self.env['product.template.attribute.value'].search([
                        ('product_tmpl_id', '=', product_template.id),
                        ('price_extra', '=', 3)
                    ]).ids
                )],
            }),
        ]

        self.start_tour("/", 'tour_shop_multi_checkbox', login="portal")

    def test_11_shop_editor_set_product_ribbon(self):
        self.start_tour("/", 'shop_editor_set_product_ribbon', login="admin")

    def test_12_multi_checkbox_attribute_single_value(self):
        attribute = self.env['product.attribute'].create([
            {
                'name': 'Toppings',
                'create_variant': 'no_variant',
                'display_type': 'multi',
                'value_ids': [(0, 0, {'name': 'cheese'})],
            },
        ])
        self.env['product.template'].create({
            'name': 'Burger',
            'is_published': True,
            'list_price': 750,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute.id,
                    'value_ids': [(6, 0, attribute.value_ids.ids)],
                }),
            ],
        })

        self.start_tour("/", 'tour_shop_multi_checkbox_single_value', login="website_user")

# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64

from odoo.addons.base.tests.common import HttpCaseWithUserDemo, HttpCaseWithUserPortal
from odoo.modules.module import get_module_resource
from odoo.tests import tagged

@tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo, HttpCaseWithUserPortal):

    def setUp(self):
        super().setUp()
        self.env.company.country_id = self.env.ref('base.us')
        # create a template
        product_template = self.env['product.template'].create({
            'name': 'Test Product',
            'is_published': True,
            'list_price': 750,
        })

        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 10})
        product_template.taxes_id = tax

        product_attribute = self.env['product.attribute'].create({
            'name': 'Legs',
            'visibility': 'visible',
            'sequence': 10,
        })
        product_attribute_value_1 = self.env['product.attribute.value'].create({
            'name': 'Steel - Test',
            'attribute_id': product_attribute.id,
            'sequence': 1,
        })
        product_attribute_value_2 = self.env['product.attribute.value'].create({
            'name': 'Aluminium',
            'attribute_id': product_attribute.id,
            'sequence': 2,
        })

        # set attribute and attribute values on the template
        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, [product_attribute_value_1.id, product_attribute_value_2.id])]
        }])

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env['product.template.attribute.value'] \
            .search([('product_tmpl_id', '=', product_template.id)])

        for ptav in product_template_attribute_values:
            if ptav.name == "Steel - Test":
                ptav.price_extra = 0
            else:
                ptav.price_extra = 50.4

        # Update the pricelist currency regarding env.company_id currency_id in case company has changed currency with COA installation.
        website = self.env['website'].get_current_website()
        pricelist = website.get_current_pricelist()
        pricelist.write({'currency_id': self.env.company.currency_id.id})

    def test_01_admin_shop_customize_tour(self):
        # Enable Variant Group
        self.env.ref('product.group_product_variant').write({'users': [(4, self.env.ref('base.user_admin').id)]})
        self.start_tour(self.env['website'].get_client_action_url('/shop?search=Test Product'), 'shop_customize', login="admin", timeout=120)

    def test_02_admin_shop_custom_attribute_value_tour(self):
        # Make sure pricelist rule exist
        self.product_attribute_1 = self.env['product.attribute'].create({
            'name': 'Legs',
            'sequence': 10,
        })
        product_attribute_value_1 = self.env['product.attribute.value'].create({
            'name': 'Steel',
            'attribute_id': self.product_attribute_1.id,
            'sequence': 1,
        })
        product_attribute_value_2 = self.env['product.attribute.value'].create({
            'name': 'Aluminium',
            'attribute_id': self.product_attribute_1.id,
            'sequence': 2,
        })
        product_attribute_2 = self.env['product.attribute'].create({
            'name': 'Color',
            'sequence': 20,
        })
        product_attribute_value_3 = self.env['product.attribute.value'].create({
            'name': 'White',
            'attribute_id': product_attribute_2.id,
            'sequence': 1,
        })
        product_attribute_value_4 = self.env['product.attribute.value'].create({
            'name': 'Black',
            'attribute_id': product_attribute_2.id,
            'sequence': 2,
        })

        # Create product template
        self.product_product_4_product_template = self.env['product.template'].create({
            'name': 'Customizable Desk (TEST)',
            'standard_price': 500.0,
            'list_price': 750.0,
        })

        # Generate variants
        self.env['product.template.attribute.line'].create([{
            'product_tmpl_id': self.product_product_4_product_template.id,
            'attribute_id': self.product_attribute_1.id,
            'value_ids': [(4, product_attribute_value_1.id), (4, product_attribute_value_2.id)],
        }, {
            'product_tmpl_id': self.product_product_4_product_template.id,
            'attribute_id': product_attribute_2.id,
            'value_ids': [(4, product_attribute_value_3.id), (4, product_attribute_value_4.id)],

        }])
        product_template = self.product_product_4_product_template

        # Add Custom Attribute
        product_attribute_value_7 = self.env['product.attribute.value'].create({
            'name': 'Custom TEST',
            'attribute_id': self.product_attribute_1.id,
            'sequence': 3,
            'is_custom': True
        })
        self.product_product_4_product_template.attribute_line_ids[0].write({'value_ids': [(4, product_attribute_value_7.id)]})

        img_path = get_module_resource('product', 'static', 'img', 'product_product_11-image.png')
        img_content = base64.b64encode(open(img_path, "rb").read())
        self.product_product_11_product_template = self.env['product.template'].create({
            'name': 'Conference Chair (TEST)',
            'website_sequence': 9999, # laule
            'image_1920': img_content,
            'list_price': 16.50,
        })

        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.product_product_11_product_template.id,
            'attribute_id': self.product_attribute_1.id,
            'value_ids': [(4, product_attribute_value_1.id), (4, product_attribute_value_2.id)],
        })
        self.product_product_11_product_template.attribute_line_ids[0].product_template_value_ids[1].price_extra = 6.40

        # Setup a second optional product
        self.product_product_1_product_template = self.env['product.template'].create({
            'name': 'Chair floor protection',
            'list_price': 12.0,
        })

        # fix runbot, sometimes one pricelist is chosen, sometimes the other...
        pricelists = self.env['website'].get_current_website().get_current_pricelist() | self.env.ref('product.list0')

        for pricelist in pricelists:
            if not pricelist.item_ids.filtered(lambda i: i.product_tmpl_id == product_template and i.price_discount == 20):
                self.env['product.pricelist.item'].create({
                    'base': 'list_price',
                    'applied_on': '1_product',
                    'pricelist_id': pricelist.id,
                    'product_tmpl_id': product_template.id,
                    'price_discount': 20,
                    'min_quantity': 2,
                    'compute_price': 'formula',
                })

            pricelist.discount_policy = 'without_discount'

        self.start_tour("/", 'shop_custom_attribute_value', login="admin")

    def test_03_public_tour_shop_dynamic_variants(self):
        """ The goal of this test is to make sure product variants with dynamic
        attributes can be created by the public user (when being added to cart).
        """

        # create the attribute
        product_attribute = self.env['product.attribute'].create({
            'name': "Dynamic Attribute",
            'create_variant': 'dynamic',
        })

        # create the attribute values
        product_attribute_values = self.env['product.attribute.value'].create([{
            'name': "Dynamic Value 1",
            'attribute_id': product_attribute.id,
            'sequence': 1,
        }, {
            'name': "Dynamic Value 2",
            'attribute_id': product_attribute.id,
            'sequence': 2,
        }])

        # create the template
        product_template = self.env['product.template'].create({
            'name': 'Dynamic Product',
            'website_published': True,
            'list_price': 10,
        })

        # set attribute and attribute values on the template
        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, product_attribute_values.ids)]
        }])

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env['product.template.attribute.value'] \
            .search([('product_tmpl_id', '=', product_template.id)])

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
        })

        # create the attribute values
        product_attribute_values = self.env['product.attribute.value'].create([{
            'name': "My Value 1",
            'attribute_id': product_attribute.id,
            'sequence': 1,
        }, {
            'name': "My Value 2",
            'attribute_id': product_attribute.id,
            'sequence': 2,
        }, {
            'name': "My Value 3",
            'attribute_id': product_attribute.id,
            'sequence': 3,
        }])

        # create the template
        product_template = self.env['product.template'].create({
            'name': 'Test Product 2',
            'is_published': True,
        })

        # set attribute and attribute values on the template
        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, product_attribute_values.ids)]
        }])

        # set a different price on the variants to differentiate them
        product_template_attribute_values = self.env['product.template.attribute.value'] \
            .search([('product_tmpl_id', '=', product_template.id)])

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

        # create the attribute
        product_attribute_no_variant = self.env['product.attribute'].create({
            'name': "No Variant Attribute",
            'create_variant': 'no_variant',
        })

        # create the attribute value
        product_attribute_value_no_variant = self.env['product.attribute.value'].create({
            'name': "No Variant Value",
            'attribute_id': product_attribute_no_variant.id,
        })

        # create the template
        product_template = self.env['product.template'].create({
            'name': 'Test Product 3',
            'website_published': True,
        })

        # set attribute and attribute value on the template
        ptal = self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute_no_variant.id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, product_attribute_value_no_variant.ids)]
        }])

        # set a price on the value
        ptal.product_template_value_ids.price_extra = 10

        self.start_tour("/", 'tour_shop_no_variant_attribute', login="demo")

    def test_06_admin_list_view_b2c(self):
        self.env.ref('product.group_product_variant').write({'users': [(4, self.env.ref('base.user_admin').id)]})

        # activate b2c
        config = self.env['res.config.settings'].create({})
        config.show_line_subtotals_tax_selection = "tax_included"
        config.execute()

        self.start_tour(self.env['website'].get_client_action_url('/shop?search=Test Product'), 'shop_list_view_b2c', login="admin")

    def test_07_editor_shop(self):
        self.env["product.pricelist"].create({
            "name": "EUR Pricelist",
            "selectable": True,
            "website_id": self.env.ref("website.default_website").id,
            "country_group_ids": [(4, self.env.ref('base.europe').id)],
            "sequence": 3,
            "currency_id": self.env.ref("base.EUR").id,
        })

        self.start_tour("/", 'shop_editor', login="admin")

    def test_08_portal_tour_archived_variant_multiple_attributes(self):
        """The goal of this test is to make sure that an archived variant with multiple
        attributes only disabled other options if only one is missing or all are selected.

        Using "portal" to have various users in the tests.
        """

        attribute_1, attribute_2, attribute_3 = self.env['product.attribute'].create([
            {
                'name': 'Size',
                'create_variant': 'always',
            },
            {
                'name': 'Color',
                'create_variant': 'always',
            },
            {
                'name': 'Brand',
                'create_variant': 'always',
            },
        ])

        attribute_values = self.env['product.attribute.value'].create([
            {
                'name': 'Large',
                'attribute_id': attribute_1.id,
                'sequence': 1,
            },
            {
                'name': 'Small',
                'attribute_id': attribute_1.id,
                'sequence': 2,
            },
            {
                'name': 'White',
                'attribute_id': attribute_2.id,
                'sequence': 1,
            },
            {
                'name': 'Black',
                'attribute_id': attribute_2.id,
                'sequence': 2,
            },
            {
                'name': 'Brand A',
                'attribute_id': attribute_3.id,
                'sequence': 1,
            },
            {
                'name': 'Brand B',
                'attribute_id': attribute_3.id,
                'sequence': 2,
            },
        ])

        product_template = self.env['product.template'].create({
            'name': 'Test Product 2',
            'is_published': True,
        })

        self.env['product.template.attribute.line'].create([
            {
                'attribute_id': attribute_1.id,
                'product_tmpl_id': product_template.id,
                'value_ids': [(6, 0, attribute_values.filtered(lambda v: v.attribute_id == attribute_1).ids)],
            },
            {
                'attribute_id': attribute_2.id,
                'product_tmpl_id': product_template.id,
                'value_ids': [(6, 0, attribute_values.filtered(lambda v: v.attribute_id == attribute_2).ids)],
            },
            {
                'attribute_id': attribute_3.id,
                'product_tmpl_id': product_template.id,
                'value_ids': [(6, 0, attribute_values.filtered(lambda v: v.attribute_id == attribute_3).ids)],
            },
        ])

        product_template.product_variant_ids[-1].active = False

        self.start_tour("/", 'tour_shop_archived_variant_multi', login="portal")

    def test_09_pills_variant(self):
        """The goal of this test is to make sure that you can click anywhere on a pill
        and still trigger a variant change. The radio input be visually hidden.

        Using "portal" to have various users in the tests.
        """

        attribute_1 = self.env['product.attribute'].create([
            {
                'name': 'Size',
                'create_variant': 'always',
                'display_type': 'pills',
            },
        ])

        attribute_values = self.env['product.attribute.value'].create([
            {
                'name': 'Large',
                'attribute_id': attribute_1.id,
                'sequence': 1,
            },
            {
                'name': 'Small',
                'attribute_id': attribute_1.id,
                'sequence': 2,
            },
        ])

        product_template = self.env['product.template'].create({
            'name': 'Test Product 2',
            'is_published': True,
        })

        self.env['product.template.attribute.line'].create([
            {
                'attribute_id': attribute_1.id,
                'product_tmpl_id': product_template.id,
                'value_ids': [(6, 0, attribute_values.ids)],
            },
        ])

        self.start_tour("/", 'test_09_pills_variant', login="portal")

    def test_10_shop_editor_set_product_ribbon(self):
        self.start_tour("/", 'shop_editor_set_product_ribbon', login="admin")

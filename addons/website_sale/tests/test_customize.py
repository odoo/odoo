# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def setUp(self):
        super(TestUi, self).setUp()
        # create a template
        product_template = self.env['product.template'].create({
            'name': 'Test Product',
            'is_published': True,
            'list_price': 750,
        })

        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 10})
        product_template.taxes_id = tax

        product_attribute = self.env.ref('product.product_attribute_1')
        product_attribute_value_1 = self.env.ref('product.product_attribute_value_1')
        product_attribute_value_2 = self.env.ref('product.product_attribute_value_2')

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
            if ptav.name == "Steel":
                ptav.price_extra = 0
            else:
                ptav.price_extra = 50.4

    def test_01_admin_shop_customize_tour(self):
        self.start_tour("/", 'shop_customize', login="admin")

    def test_02_admin_shop_custom_attribute_value_tour(self):
        # Make sure pricelist rule exist
        product_template = self.env.ref('product.product_product_4_product_template')

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
            'list_price': 0,
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
        self.start_tour("/", 'shop_list_view_b2c', login="admin")

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import base64 

import odoo.tests
from odoo.modules.module import get_module_resource


@odoo.tests.tagged('post_install', '-at_install')
class TestUi(odoo.tests.HttpCase):

    def setUp(self):
        super(TestUi, self).setUp()

        # Setup attributes and attributes values
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

        # Apply a price_extra for the attribute Aluminium
        self.product_product_4_product_template.attribute_line_ids[0].product_template_value_ids[1].price_extra = 50.40


        # Add a Custom attribute
        product_attribute_value_7 = self.env['product.attribute.value'].create({
            'name': 'Custom',
            'attribute_id': self.product_attribute_1.id,
            'sequence': 3,
            'is_custom': True
        })
        self.product_product_4_product_template.attribute_line_ids[0].write({'value_ids': [(4, product_attribute_value_7.id)]})

        # Disable the aluminium + black product
        self.product_product_4_product_template.product_variant_ids[3].active = False

        # Setup a first optional product
        img_path = get_module_resource('product', 'static', 'img', 'product_product_11-image.png')
        img_content = base64.b64encode(open(img_path, "rb").read())
        self.product_product_11_product_template = self.env['product.template'].create({
            'name': 'Conference Chair (TEST)',
            'image_1920': img_content,
            'list_price': 16.50,
        })

        self.env['product.template.attribute.line'].create({
            'product_tmpl_id': self.product_product_11_product_template.id,
            'attribute_id': self.product_attribute_1.id,
            'value_ids': [(4, product_attribute_value_1.id), (4, product_attribute_value_2.id)],
        })
        self.product_product_4_product_template.optional_product_ids = [(4, self.product_product_11_product_template.id)]

        # Setup a second optional product
        self.product_product_1_product_template = self.env['product.template'].create({
            'name': 'Chair floor protection',
            'list_price': 12.0,
        })
        self.product_product_11_product_template.optional_product_ids = [(4, self.product_product_1_product_template.id)]


    def test_01_product_configurator(self):
        # To be able to test the product configurator, admin user must have access to "variants" feature, so we give him the right group for that
        self.env.ref('base.user_admin').write({'groups_id': [(4, self.env.ref('product.group_product_variant').id)]})

        self.start_tour("/web", 'sale_product_configurator_tour', login="admin")

    def test_02_product_configurator_advanced(self):
        # group_product_variant: use the product configurator
        # group_sale_pricelist: display the pricelist to determine when it is changed after choosing
        # group_delivery_invoice_address: show the shipping address (needed for a trigger)
        #                       the partner
        self.env.ref('base.user_admin').write({
            'groups_id': [
                (4, self.env.ref('product.group_product_variant').id),
                (4, self.env.ref('product.group_product_pricelist').id),
                (4, self.env.ref('sale.group_delivery_invoice_address').id),
            ],
        })

        # Prepare relevant test data
        # This is not included in demo data to avoid useless noise
        product_attributes = self.env['product.attribute'].create([{
            'name': 'PA1',
            'display_type': 'radio',
            'create_variant': 'dynamic'
        }, {
            'name': 'PA2',
            'display_type': 'radio',
            'create_variant': 'always'
        }, {
            'name': 'PA3',
            'display_type': 'radio',
            'create_variant': 'dynamic'
        }, {
            'name': 'PA4',
            'display_type': 'select',
            'create_variant': 'no_variant'
        }, {
            'name': 'PA5',
            'display_type': 'select',
            'create_variant': 'no_variant'
        }, {
            'name': 'PA7',
            'display_type': 'color',
            'create_variant': 'no_variant'
        }, {
            'name': 'PA8',
            'display_type': 'radio',
            'create_variant': 'no_variant'
        }])

        self.env['product.attribute.value'].create([{
            'name': 'PAV' + str(i),
            'is_custom': i == 9,
            'attribute_id': product_attribute.id
        } for i in range(1, 11) for product_attribute in product_attributes])

        product_template = self.product_product_4_product_template

        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, product_attribute.value_ids.ids)],
        } for product_attribute in product_attributes])

        self.start_tour("/web", 'sale_product_configurator_advanced_tour', login="admin")

    def test_03_product_configurator_edition(self):
        # To be able to test the product configurator, admin user must have access to "variants" feature, so we give him the right group for that
        self.env.ref('base.user_admin').write({'groups_id': [(4, self.env.ref('product.group_product_variant').id)]})

        self.start_tour("/web", 'sale_product_configurator_edition_tour', login="admin")

    def test_04_product_configurator_single_custom_value(self):
        # group_product_variant: use the product configurator
        # group_sale_pricelist: display the pricelist to determine when it is changed after choosing
        #                       the partner
        self.env.ref('base.user_admin').write({
            'groups_id': [
                (4, self.env.ref('product.group_product_variant').id),
                (4, self.env.ref('product.group_product_pricelist').id),
            ],
        })

        # Prepare relevant test data
        # This is not included in demo data to avoid useless noise
        product_attributes = self.env['product.attribute'].create([{
            'name': 'product attribute',
            'display_type': 'radio',
            'create_variant': 'always'
        }])

        product_attribute_values = self.env['product.attribute.value'].create([{
            'name': 'single product attribute value',
            'is_custom': True,
            'attribute_id': product_attributes[0].id
        }])

        product_template = self.product_product_4_product_template

        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attributes[0].id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, [product_attribute_values[0].id])]
        }])

        self.start_tour("/web", 'sale_product_configurator_single_custom_attribute_tour', login="admin")

    def test_05_product_configurator_pricelist(self):
        """The goal of this test is to make sure pricelist rules are correctly
        applied on the backend product configurator.
        Also testing B2C setting: no impact on the backend configurator.
        """

        admin = self.env.ref('base.user_admin')

        # Activate B2C
        self.env.ref('account.group_show_line_subtotals_tax_excluded').users -= admin
        self.env.ref('account.group_show_line_subtotals_tax_included').users |= admin

        # Active pricelist on SO
        self.env.ref('product.group_product_pricelist').users |= admin

        # Add a 15% tax on desk
        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 15})
        self.product_product_4_product_template.taxes_id = tax

        # Remove tax from Conference Chair and Chair floor protection
        self.product_product_1_product_template.taxes_id = None
        self.product_product_11_product_template.taxes_id = None

        # Make sure pricelist rule exist
        product_template = self.product_product_4_product_template
        pricelist = self.env.ref('product.list0')

        if not pricelist.item_ids.filtered(lambda i: i.product_tmpl_id == product_template and i.applied_on == '1_product' and i.price_discount == 20):
            self.env['product.pricelist.item'].create({
                'base': 'list_price',
                'applied_on': '1_product',
                'pricelist_id': pricelist.id,
                'product_tmpl_id': product_template.id,
                'price_discount': 20,
                'min_quantity': 2,
                'compute_price': 'formula',
            })

        self.start_tour("/web", 'sale_product_configurator_pricelist_tour', login="admin")

    def test_06_product_configurator_optional_products(self):
        """The goal of this test is to check that the product configurator
        window opens correctly and lets you select optional products even
        if the main product does not have variants.
        """

        # add an optional product to the office chair and the custo desk for testing purposes
        office_chair = self.env['product.product'].create({
            'name': 'Office Chair Black',
        })

        custo_desk = self.product_product_4_product_template.product_variant_ids[0]
        office_chair.update({
            'optional_product_ids': [(6, 0, [self.product_product_1_product_template.id])]
        })
        custo_desk.update({
            'optional_product_ids': [(6, 0, [office_chair.product_tmpl_id.id, self.product_product_11_product_template.id])]
        })
        self.start_tour("/web", 'sale_product_configurator_optional_products_tour', login="admin")

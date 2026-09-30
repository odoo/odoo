# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale.tests.product_configurator_common import TestProductConfiguratorCommon


@tagged('post_install', '-at_install')
class TestProductConfiguratorUi(TestProductConfiguratorCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')

        # Adding sale users to test the access rights
        cls.salesman = mail_new_test_user(
            cls.env,
            name='Salesman',
            login='salesman',
            password='salesman',
            groups='sales_team.group_sale_salesman',
        )
        cls.salesman.group_ids += cls.env.ref('product.group_product_manager')

        # Setup partner since user salesman don't have the right to create it on the fly
        cls.env['res.partner'].create({'name': 'Tajine Saucisse'})

    def test_01_product_configurator(self):
        self.env.ref('base.user_admin').write({'group_ids': [(4, self.env.ref('product.group_product_variant').id)]})
        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 15})
        self.product_product_custo_desk.taxes_id = tax
        self.product_product_conf_chair_floor_protect.taxes_id = tax
        self.product_product_conf_chair.taxes_id = tax
        self.start_tour("/odoo", 'sale_product_configurator_tour', login='salesman')

    def test_02_product_configurator_advanced(self):
        # group_delivery_invoice_address: show the shipping address (needed for a trigger)
        self.salesman.write({
            'group_ids': [(4, self.env.ref('account.group_delivery_invoice_address').id)],
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
            'display_type': 'image',
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

        product_attribute_no_variant_single_pav = self.env['product.attribute'].create({
            'name': 'PA9',
            'display_type': 'radio',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'Single PAV'}),
            ]
        })

        product_template = self.product_product_custo_desk

        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, product_attribute.value_ids.ids)],
        } for product_attribute in (product_attributes + product_attribute_no_variant_single_pav)])

        self.assertEqual(len(product_template.product_variant_ids), 0)
        self.assertEqual(
            len(product_template.product_variant_ids.product_template_attribute_value_ids), 0,
        )

        self.start_tour("/odoo", 'sale_product_configurator_advanced_tour', login='salesman')

        # Ensures dynamic create variants have been created by the configurator
        self.assertEqual(len(product_template.product_variant_ids), 1)
        self.assertEqual(
            len(product_template.product_variant_ids.product_template_attribute_value_ids), 5
        )

    def test_03_product_configurator_edition(self):
        # Required to see `pricelist_id` in the view
        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('product.group_product_pricelist').id)]})
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
        self.start_tour("/odoo", 'sale_product_configurator_edition_tour', login='salesman')

    def test_04_product_configurator_single_custom_value(self):
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

        product_template = self.product_product_custo_desk

        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attributes[0].id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, [product_attribute_values[0].id])]
        }])

        self.start_tour(
            "/odoo",
            'sale_product_configurator_single_custom_attribute_tour',
            login='salesman'
        )

    def test_05_product_configurator_pricelist(self):
        """The goal of this test is to make sure pricelist rules are correctly applied on the
        backend product configurator.
        Also testing B2C setting: no impact on the backend configurator.
        """

        # Required to see `pricelist_id` in the view
        self.env.ref('base.group_user').write({'implied_ids': [(4, self.env.ref('product.group_product_pricelist').id)]})

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

        self.env['res.partner'].create({
            'name': 'Azure Interior',
            'email': 'azure.Interior24@example.com',
            'city': 'Fremont',
        })
        # Add a 15% tax on desk
        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 15})
        self.product_product_custo_desk.taxes_id = tax

        # Remove tax from Conference Chair and Chair floor protection
        self.product_product_conf_chair.taxes_id = None
        self.product_product_conf_chair_floor_protect.taxes_id = None
        self.start_tour("/odoo", 'sale_product_configurator_pricelist_tour', login='salesman')

    def test_06_product_configurator_optional_products(self):
        """The goal of this test is to check that the product configurator window opens correctly
        and lets you select optional products even if the main product does not have variants.
        """
        # add an optional product to the office chair and the custo desk for testing purposes
        office_chair = self.env['product.product'].create({
            'name': 'Office Chair Black',
        })

        custo_desk = self.product_product_custo_desk.product_variant_ids[0]
        office_chair.update({
            'optional_product_ids': [(6, 0, [self.product_product_conf_chair_floor_protect.id])]
        })
        custo_desk.update({
            'optional_product_ids': [
                (6, 0, [office_chair.product_tmpl_id.id, self.product_product_conf_chair.id])
            ]
        })

        self.salesman.group_ids += self.env.ref('sale.group_warning_sale')
        self.product_product_conf_chair.sale_line_warn_msg = 'sold'
        self.product_product_custo_desk.optional_product_ids = [
            (4, self.product_product_conf_chair.id)
        ]
        self.start_tour(
            "/odoo", 'sale_product_configurator_optional_products_tour', login='salesman'
        )

    def test_07_product_configurator_recursive_optional_products(self):
        """The goal of this test is to check that the product configurator works correctly with
        recursive optional products.
        """
        # create products with recursive optional products
        self.product_product_conf_chair_floor_protect.update({
            'optional_product_ids': [(6, 0, [self.product_product_conf_chair.id])]
        })
        self.product_product_conf_chair.optional_product_ids = [
            (4, self.product_product_conf_chair_floor_protect.id)
        ]
        self.product_product_conf_chair_floor_protect.optional_product_ids = [
            (4, self.product_product_conf_chair.id)
        ]
        self.product_product_custo_desk.optional_product_ids = [
            (4, self.product_product_conf_chair.id)
        ]
        self.product_product_conf_chair.optional_product_ids = [
            (4, self.product_product_custo_desk.id)
        ]
        self.start_tour(
            "/odoo", 'sale_product_configurator_recursive_optional_products_tour', login='salesman'
        )

    def test_product_configurator_update_custom_values(self):
        self.start_tour(
            "/odoo", 'sale_product_configurator_custom_value_update_tour', login='salesman',
        )
        order = self.env['sale.order'].search([], order='id desc', limit=1)
        self.assertEqual(
            order.order_line.product_custom_attribute_value_ids.custom_value,
            "123456",
        )

    def test_product_attribute_multi_type(self):
        """The goal of this test is to verify that the product configurator dialog box opens
            correctly when the product attribute display type is set to "multi" and only a
            single value can be chosen.
        """

        attribute_topping = self.env['product.attribute'].create({
            'name': 'Toppings',
            'display_type': 'multi',
            'create_variant': 'no_variant',
            'value_ids': [
                Command.create({'name': 'Cheese'}),
            ]
        })

        product_template = self.env['product.template'].create({
            'name': 'Big Burger',
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': attribute_topping.id,
                    'value_ids': [Command.set(attribute_topping.value_ids.ids)],
                }),
            ],
        })
        self.env['res.partner'].create({
            'name': "Azure",
            'email': "azure@example.com",
        })

        self.start_tour("/odoo", 'product_attribute_multi_type', login="salesman")

        sol = self.env['sale.order.line'].search([
            ('product_id', '=', product_template.product_variant_id.id),
        ])
        self.assertTrue(sol)
        self.assertEqual(
            sol.product_no_variant_attribute_value_ids,
            product_template.attribute_line_ids.product_template_value_ids,
        )

    def test_product_configurator_uom_selection(self):
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

        self.env.ref('base.group_user').write({
            'implied_ids': [
                # Required to set pricelist
                Command.link(self.env.ref('product.group_product_pricelist').id),
                # Required to set uom in configurator
                Command.link(self.group_uom.id),
            ],
        })

        self.product_product_custo_desk.uom_id = self.uom_unit
        self.assertEqual(self.product_product_custo_desk.uom_id, self.uom_unit)
        self.product_product_custo_desk.uom_ids += self.uom_dozen
        self.product_product_conf_chair.uom_ids = self.uom_dozen

        self.assertIn(self.uom_dozen, self.product_product_custo_desk.uom_ids)

        # Add a 15% tax on desk
        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 15})
        self.product_product_custo_desk.taxes_id = tax

        # Remove tax from Conference Chair and Chair floor protection
        self.product_product_conf_chair.taxes_id = None
        self.product_product_conf_chair_floor_protect.taxes_id = None
        self.assertTrue(self.salesman._has_group('product.group_product_pricelist'))
        self.start_tour("/odoo", 'sale_product_configurator_uom_tour', login='salesman')

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import HttpCase, tagged

from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.sale_product_configurator.tests.common import TestProductConfiguratorCommon


@tagged('post_install', '-at_install')
class TestProductConfiguratorUi(HttpCase, TestProductConfiguratorCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Adding sale users to test the access rights
        cls.salesman = mail_new_test_user(
            cls.env,
            name='Salesman',
            login='salesman',
            password='salesman',
            groups='sales_team.group_sale_salesman',
        )

        # Setup partner since user salesman don't have the right to create it on the fly
        cls.env['res.partner'].create({'name': 'Tajine Saucisse'})

    def test_01_product_configurator(self):
        self.start_tour("/web", 'sale_product_configurator_tour', login='salesman')

    def test_02_product_configurator_advanced(self):
        # group_delivery_invoice_address: show the shipping address (needed for a trigger)
        self.salesman.write({
            'groups_id': [(4, self.env.ref('account.group_delivery_invoice_address').id)],
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

        product_attribute_no_variant_single_pav = self.env['product.attribute'].create({
            'name': 'PA9',
            'display_type': 'radio',
            'create_variant': 'no_variant'
        })

        self.env['product.attribute.value'].create({
            'name': 'Single PAV',
            'attribute_id': product_attribute_no_variant_single_pav.id
        })

        product_attributes += product_attribute_no_variant_single_pav

        product_template = self.product_product_custo_desk

        self.env['product.template.attribute.line'].create([{
            'attribute_id': product_attribute.id,
            'product_tmpl_id': product_template.id,
            'value_ids': [(6, 0, product_attribute.value_ids.ids)],
        } for product_attribute in product_attributes])

        self.assertEqual(len(product_template.product_variant_ids), 0)
        self.assertEqual(
            len(product_template.product_variant_ids.product_template_attribute_value_ids), 0,
        )

        self.start_tour("/web", 'sale_product_configurator_advanced_tour', login='salesman')

        # Ensures dynamic create variants have been created by the configurator
        self.assertEqual(len(product_template.product_variant_ids), 1)
        self.assertEqual(
            len(product_template.product_variant_ids.product_template_attribute_value_ids), 5
        )

    def test_03_product_configurator_edition(self):
        self.start_tour("/web", 'sale_product_configurator_edition_tour', login='salesman')

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
            "/web",
            'sale_product_configurator_single_custom_attribute_tour',
            login='salesman'
        )

    def test_05_product_configurator_pricelist(self):
        """The goal of this test is to make sure pricelist rules are correctly applied on the
        backend product configurator.
        Also testing B2C setting: no impact on the backend configurator.
        """

        # Required to see `pricelist_id` in the view
        self.salesman.write({
            'groups_id': [(4, self.env.ref('product.group_product_pricelist').id)],
        })

        # Add a 15% tax on desk
        tax = self.env['account.tax'].create({'name': "Test tax", 'amount': 15})
        self.product_product_custo_desk.taxes_id = tax

        # Remove tax from Conference Chair and Chair floor protection
        self.product_product_conf_chair.taxes_id = None
        self.product_product_conf_chair_floor_protect.taxes_id = None
        self.start_tour("/web", 'sale_product_configurator_pricelist_tour', login='salesman')

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
        self.product_product_conf_chair.sale_line_warn = 'warning'
        self.product_product_conf_chair.sale_line_warn_msg = 'sold'
        self.product_product_custo_desk.optional_product_ids = [
            (4, self.product_product_conf_chair.id)
        ]
        self.start_tour(
            "/web", 'sale_product_configurator_optional_products_tour', login='salesman'
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
            "/web", 'sale_product_configurator_recursive_optional_products_tour', login='salesman'
        )

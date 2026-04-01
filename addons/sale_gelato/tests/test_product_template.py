# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.sale_gelato.tests.common import GelatoCommon


@tagged('post_install', '-at_install')
class TestProductTemplate(GelatoCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env['product.attribute'].search([('name', 'in', ['Color', 'Size'])]).active = False
        cls.env['product.attribute.value'].search([]).active = False

        cls.template_data_two_variants = dict(
            cls.template_data_one_variant,
            variants=[
                *cls.template_data_one_variant['variants'],
                {
                    "productUid": "l_orange_tshirt_uid",
                    "variantOptions": [
                        {"name": "Size", "value": "L"},
                        {'name': 'Color', 'value': 'Orange'},
                    ],
                    "imagePlaceholders": [{"printArea": "front"}, {'printArea': 'back'}],
                },
            ],
        )
        cls.template_data_three_variants = dict(
            cls.template_data_two_variants,
            variants=[
                *cls.template_data_two_variants['variants'],
                {
                    "productUid": "l_white_tshirt_uid",
                    "variantOptions": [
                        {"name": "Size", "value": "L"},
                        {'name': 'Color', 'value': 'Red'},
                    ],
                    "imagePlaceholders": [{"printArea": "front"}, {'printArea': 'back'}],
                },
            ],
        )

    def _create_attribute(self, name):
        return self.env['product.attribute'].create({'name': name, 'create_variant': 'always'})

    def test_creating_attributes_sets_product_uid_on_template(self):
        """Test that the product UID is assigned to the template if there is only one variant."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_one_variant)
        self.assertEqual(self.gelato_template.gelato_product_uid, 'm_orange_tshirt_uid')

    def test_synchronizing_template_creates_product_variants(self):
        """Test that the correct amount of product variants are created."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_three_variants)
        self.assertEqual(self.gelato_template.product_variant_count, 3)

    def test_synchronizing_template_creates_missing_attributes(self):
        """Test that missing attributes are created."""
        self.assertEqual(
            self.env['product.attribute'].search_count([('name', 'in', ['Color', 'Size'])]),
            0,
            msg="Color and Size attributes should not exist before synchronization.",
        )
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        self.assertEqual(
            self.env['product.attribute'].search_count([('name', 'in', ['Color', 'Size'])]), 2
        )

    def test_synchronizing_template_assigns_new_attributes(self):
        """Test that newly created attributes are assigned to the template."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        added_attribute_names = self.gelato_template.attribute_line_ids.attribute_id.mapped('name')
        self.assertEqual(added_attribute_names, ['Size', 'Color'])

    def test_synchronizing_template_assigns_existing_attributes(self):
        """Test that already existing attributes are assigned to the template instead of creating
        new ones."""
        existing_color_attribute = self._create_attribute(name='Color')
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        assigned_template_attribute = self.gelato_template.attribute_line_ids[0].attribute_id
        self.assertEqual(
            assigned_template_attribute,
            existing_color_attribute,
            msg="Existing attributes should be used instead of creating new ones.",
        )

    def test_synchronizing_template_creates_missing_attribute_values(self):
        """Test that missing attribute values are created."""
        self.assertEqual(
            self.env['product.attribute.value'].search_count([('name', 'in', ['Orange', 'Red'])]),
            0,
            "Red and Orange attribute values should exist before synchronization.",
        )
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_three_variants)
        self.assertEqual(
            self.env['product.attribute.value'].search_count([('name', 'in', ['Orange', 'Red'])]),
            2,
            "Red and Orange attribute values should exist before synchronization.",
        )

    def test_synchronizing_template_assigns_new_attribute_values(self):
        """Test that newly created attribute values are assigned to the template."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_three_variants)
        self.assertEqual(
            self.gelato_template.attribute_line_ids.value_ids.mapped('name'),
            ['M', 'L', 'Orange', 'Red'],
        )

    def test_synchronizing_template_assigns_existing_attribute_values(self):
        """Test that already existing attribute values are assigned to the template instead of
        creating new ones."""
        color_attribute = self._create_attribute(name="Color")
        orange_attribute_value = self.env['product.attribute.value'].create({
            'name': "Orange",
            'attribute_id': color_attribute.id,
        })
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        variant_attribute_value = self.gelato_template.attribute_line_ids.value_ids[0]
        self.assertEqual(
            variant_attribute_value,
            orange_attribute_value,
            msg="Existing attribute values should be used instead of creating new ones.",
        )

    def test_creating_attributes_sets_product_uids_on_variants(self):
        """Test that all created variants are assigned a Gelato product UID."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        self.assertEqual(
            self.gelato_template.product_variant_ids.mapped('gelato_product_uid'),
            ['m_orange_tshirt_uid', 'l_orange_tshirt_uid'],
        )

    def test_creating_print_images_saves_front_as_default(self):
        """Test that 'front' and '1' image placement names are saved as 'default'."""
        self.gelato_template._create_print_images_from_gelato_info(self.template_data_one_variant)
        self.assertEqual(self.gelato_template.gelato_image_ids.mapped('name')[1], 'default')

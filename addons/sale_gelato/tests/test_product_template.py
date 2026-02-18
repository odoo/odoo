# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests import tagged

from odoo.addons.sale.tests.common import SaleCommon


@tagged('post_install', '-at_install')
class TestGelatoProductTemplate(SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.gelato_template = cls.env['product.template'].create({
            'name': 'Gelato Product Template'
        })

        cls.template_data_one_variant = {
            'id': 'c12a363e-0d4e-4d96-be4b-bf4138eb8743',
            'title': 'Classic Unisex Crewneck T-shirt',
            'description': 'Some test description',
            'variants': [
                {
                    'productUid': 'm_orange_tshirt_uid',
                    'variantOptions': [
                        {'name': 'Size', 'value': 'M'},
                        {'name': 'Color', 'value': 'Orange'},
                    ],
                    'imagePlaceholders': [{'printArea': 'front'}, {'printArea': 'back'}],
                }
            ],
        }

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

    def create_attribute(self, name):
        return self.env['product.attribute'].create({'name': name, 'create_variant': 'always'})

    def test_synchronizing_template_creates_product_variants(self):
        """Test that correct amount of product variants are created."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_three_variants)
        self.assertEqual(self.gelato_template.product_variant_count, 3)

    def test_synchronizing_template_creates_and_adds_attributes(self):
        """Test that non-existing attributes are created and added on the template."""
        self.assertEqual(
            self.env['product.attribute'].search_count([]),
            0,
            "No attributes should exist before synchronization.",
        )

        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        added_attributes = self.gelato_template.attribute_line_ids.attribute_id.mapped('name')
        self.assertEqual(added_attributes, ['Size', 'Color'])

    def test_synchronizing_template_adds_existing_attributes(self):
        """Test that already existing attribute is added on template instead of creating new one."""
        existing_color_attribute = self.create_attribute(name='Color')

        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        template_color_attribute = self.gelato_template.attribute_line_ids[0].attribute_id
        self.assertEqual(
            template_color_attribute,
            existing_color_attribute,
            msg="Existing attribute should be used instead of creating new one.",
        )

    def test_synchronizing_template_creates_and_adds_attribute_values(self):
        """Test that non-existing attribute values are created and added on the template."""
        self.assertEqual(
            self.env['product.attribute.value'].search_count([]),
            0,
            msg="No attribute values should exist.",
        )

        self.gelato_template._create_attributes_from_gelato_info(self.template_data_three_variants)
        self.assertEqual(
            self.gelato_template.attribute_line_ids.value_ids.mapped('name'),
            ['M', 'L', 'Orange', 'Red'],
        )

    def test_synchronizing_template_adds_existing_attribute_values_on_template(self):
        """Test that if attribute value already exists, it's added to the template."""
        color_attribute = self.create_attribute(name='Color')
        orange_attribute_value = self.env['product.attribute.value'].create({
            'name': 'Orange',
            'attribute_id': color_attribute.id,
        })
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        variant_attribute_value = self.gelato_template.attribute_line_ids.value_ids[0]
        self.assertEqual(
            variant_attribute_value,
            orange_attribute_value,
            msg="Existing attribute value should be assigned to the product.",
        )

    def test_creating_attributes_sets_product_uid_on_template(self):
        """Test that product UID is assigned to the template if there is only one variant."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_one_variant)
        self.assertEqual(self.gelato_template.gelato_product_uid, 'm_orange_tshirt_uid')

    def test_creating_attributes_sets_product_uids_on_variants(self):
        """Test that all created variants are assigned a Gelato product UID."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        self.assertEqual(
            self.gelato_template.product_variant_ids.mapped('gelato_product_uid'),
            ['m_orange_tshirt_uid', 'l_orange_tshirt_uid'],
        )

    def test_resynchronizing_template_removes_missing_product_variants(self):
        """Test that variants are removed from template if they are not in the new template data."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_three_variants)

        # re-synchronize the template after the variants are removed in Gelato
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        self.assertEqual(self.gelato_template.product_variant_count, 2)

    def test_resynchronizing_template_removes_missing_attribute_values(self):
        """Test that attribute values are removed from template if they are not in the new data."""
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_three_variants)
        self.assertEqual(
            self.gelato_template.attribute_line_ids.value_ids.mapped('name'),
            ['M', 'L', 'Orange', 'Red'],
        )

        # re-synchronize the template after the attribute values are removed in Gelato
        self.gelato_template._create_attributes_from_gelato_info(self.template_data_two_variants)
        self.assertEqual(
            self.gelato_template.attribute_line_ids.value_ids.mapped('name'), ['M', 'L', 'Orange']
        )

    def test_creating_print_images_saves_front_as_default(self):
        """Test that 'front' or '1' image placement names are saved as 'default'."""
        self.gelato_template._create_print_images_from_gelato_info(self.template_data_one_variant)
        self.assertEqual(self.gelato_template.gelato_image_ids.mapped('name'), ['back', 'default'])

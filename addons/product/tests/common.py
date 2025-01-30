# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests.common import bundles

from odoo.addons.uom.tests.common import UomCommon


@bundles('product.common')
class ProductCommon(UomCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.group_product_pricelist = cls.quick_ref('product.group_product_pricelist')
        cls.product_category = cls.quick_ref('product.test_category')
        cls.product = cls.quick_ref('product.test_product')
        cls.service_product = cls.quick_ref('product.test_product_service')
        cls.pricelist = cls.quick_ref('product.test_pricelist')

    @classmethod
    def get_default_groups(cls):
        groups = super().get_default_groups()
        return groups | cls.quick_ref('base.group_system')

    @classmethod
    def _enable_pricelists(cls):
        cls.env.user.groups_id += cls.group_product_pricelist

    @classmethod
    def _create_pricelist(cls, **create_vals):
        return cls.env['product.pricelist'].create({
            'name': "Test Pricelist",
            **create_vals,
        })

    @classmethod
    def _create_product(cls, **create_vals):
        return cls.env['product.product'].create({
            'name': "Test Product",
            'type': 'consu',
            'list_price': 100.0,
            'standard_price': 50.0,
            'uom_id': cls.uom_unit.id,
            'categ_id': cls.product_category.id,
            **create_vals,
        })


@bundles('product.common_attributes')
class ProductAttributesCommon(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.size_attribute = cls.quick_ref('product.test_size_attribute')
        (
            cls.size_attribute_s,
            cls.size_attribute_m,
            cls.size_attribute_l,
        ) = cls.size_attribute.value_ids

        cls.color_attribute = cls.quick_ref('product.test_color_attribute')
        (
            cls.color_attribute_red,
            cls.color_attribute_blue,
            cls.color_attribute_green,
        ) = cls.color_attribute.value_ids

        cls.no_variant_attribute = cls.quick_ref('product.test_no_variant_attribute')
        (
            cls.no_variant_attribute_extra,
            cls.no_variant_attribute_second,
        ) = cls.no_variant_attribute.value_ids

        cls.dynamic_attribute = cls.quick_ref('product.test_dynamic_attribute')


@bundles('product.common_variants')
class ProductVariantsCommon(ProductAttributesCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_template_sofa = cls.quick_ref('product.test_template_sofa')

        cls.product_template_shirt = cls.quick_ref('product.test_template_shirt')


@bundles('product.common_extended')
class TestProductCommon(ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Product environment related data
        cls.uom_dunit = cls.quick_ref('product.test_uom_dunit')

        cls.product_1 = cls.quick_ref('product.test_product_extended_1')
        cls.product_2 = cls.quick_ref('product.test_product_extended_2')

        # Kept for reduced diff in other modules (mainly stock & mrp)
        cls.prod_att_1 = cls.color_attribute
        cls.prod_attr1_v1 = cls.color_attribute_red
        cls.prod_attr1_v2 = cls.color_attribute_blue
        cls.prod_attr1_v3 = cls.color_attribute_green

        cls.product_7_template = cls.product_template_sofa

        cls.product_7_attr1_v1 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[0]
        cls.product_7_attr1_v2 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[1]
        cls.product_7_attr1_v3 = cls.product_7_template.attribute_line_ids[
            0].product_template_value_ids[2]

        cls.product_7_1 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v1)
        cls.product_7_2 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v2)
        cls.product_7_3 = cls.product_7_template._get_variant_for_combination(
            cls.product_7_attr1_v3)

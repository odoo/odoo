# -*- coding: utf-8 -*-

from contextlib import nullcontext
from unittest.mock import patch

from odoo.fields import Command

from odoo.addons.base.tests.common import BaseCommon
from odoo.addons.uom.tests.common import UomCommon


class ProductCommon(
    BaseCommon,  # enforce constant test currency (USD)
    UomCommon,
):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Ideally, this logic should be moved into sthg like a NoAccountCommon in account :D
        # Since tax fields are specified in account module, cannot be given as create values
        NO_TAXES_CONTEXT = {
            'default_taxes_id': False
        }

        cls.product_category = cls.env['product.category'].create({
            'name': 'Test Category',
        })
        cls.product = cls.env['product.product'].with_context(**NO_TAXES_CONTEXT).create({
            'name': 'Test Product',
            'detailed_type': 'consu',
            'list_price': 20.0,
            'categ_id': cls.product_category.id,
        })
        cls.service_product = cls.env['product.product'].with_context(**NO_TAXES_CONTEXT).create({
            'name': 'Test Service Product',
            'detailed_type': 'service',
            'list_price': 50.0,
            'categ_id': cls.product_category.id,
        })
        cls.consumable_product = cls.product
        cls.pricelist = cls.env['product.pricelist'].create({
            'name': 'Test Pricelist',
        })
        cls._archive_other_pricelists()

    @classmethod
    def _archive_other_pricelists(cls):
        """Do not raise if there is no pricelist(s) for a given website"""
        website_sale = cls.env['ir.module.module']._get('website_sale')
        if website_sale.state == 'installed':
            archive_context = patch('odoo.addons.website_sale.models.product_pricelist.ProductPricelist._check_website_pricelist')
        else:
            archive_context = nullcontext()

        with archive_context:
            cls.env['product.pricelist'].search([
                ('id', '!=', cls.pricelist.id),
            ]).action_archive()


class ProductAttributesCommon(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.size_attribute = cls.env['product.attribute'].create({
            'name': 'Size',
            'value_ids': [
                Command.create({'name': 'S'}),
                Command.create({'name': 'M'}),
                Command.create({'name': 'L'}),
            ]
        })
        (
            cls.size_attribute_s,
            cls.size_attribute_m,
            cls.size_attribute_l,
        ) = cls.size_attribute.value_ids

        cls.color_attribute = cls.env['product.attribute'].create({
            'name': 'Color',
            'value_ids': [
                Command.create({'name': 'red', 'sequence': 1}),
                Command.create({'name': 'blue', 'sequence': 2}),
                Command.create({'name': 'green', 'sequence': 3}),
            ],
        })
        (
            cls.color_attribute_red,
            cls.color_attribute_blue,
            cls.color_attribute_green,
        ) = cls.color_attribute.value_ids


class ProductVariantsCommon(ProductAttributesCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.product_template_sofa = cls.env['product.template'].create({
            'name': 'Sofa',
            'uom_id': cls.uom_unit.id,
            'uom_po_id': cls.uom_unit.id,
            'categ_id': cls.product_category.id,
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.color_attribute.id,
                'value_ids': [Command.set([
                    cls.color_attribute_red.id,
                    cls.color_attribute_blue.id,
                    cls.color_attribute_green.id
                ])],
            })]
        })

        cls.product_template_shirt = cls.env['product.template'].create({
            'name': 'Shirt',
            'categ_id': cls.product_category.id,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': cls.size_attribute.id,
                    'value_ids': [Command.set([cls.size_attribute_l.id])],
                }),
            ],
        })


class TestProductCommon(ProductVariantsCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Product environment related data
        cls.uom_dunit = cls.env['uom.uom'].create({
            'name': 'DeciUnit',
            'category_id': cls.uom_unit.category_id.id,
            'factor_inv': 0.1,
            'factor': 10.0,
            'uom_type': 'smaller',
            'rounding': 0.001,
        })

        cls.product_1, cls.product_2 = cls.env['product.product'].create([{
            'name': 'Courage',  # product_1
            'type': 'consu',
            'default_code': 'PROD-1',
            'uom_id': cls.uom_dunit.id,
            'uom_po_id': cls.uom_dunit.id,
        }, {
            'name': 'Wood',  # product_2
        }])

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

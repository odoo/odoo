# Part of Odoo. See LICENSE file for full copyright and licensing details.
import base64

from odoo.tools.misc import file_open
from odoo.addons.product.tests.test_configurator_common import TestProductConfiguratorCommon


class TestSaleProductConfiguratorCommon(TestProductConfiguratorCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Apply a price_extra for the attribute Aluminium
        cls.product_product_custo_desk.attribute_line_ids[0].product_template_value_ids[1].price_extra = 50.40

        # Setup a first optional product
        img_path = 'product/static/img/product_product_11-image.png'
        img_content = base64.b64encode(file_open(img_path, "rb").read())
        cls.product_product_conf_chair = cls.env['product.template'].create({
            'name': 'Conference Chair (TEST)',
            'image_1920': img_content,
            'list_price': 16.50,
        })

        cls.env['product.template.attribute.line'].create({
            'product_tmpl_id': cls.product_product_conf_chair.id,
            'attribute_id': cls.product_attribute_1.id,
            'value_ids': [(4, cls.product_attribute_value_1.id), (4, cls.product_attribute_value_2.id)],
        })
        cls.product_product_conf_chair.attribute_line_ids[0].product_template_value_ids[1].price_extra = 6.40
        cls.product_product_custo_desk.optional_product_ids = [(4, cls.product_product_conf_chair.id)]

        # Setup a second optional product
        cls.product_product_conf_chair_floor_protect = cls.env['product.template'].create({
            'name': 'Chair floor protection (TEST)',
            'list_price': 12.0,
        })
        cls.product_product_conf_chair.optional_product_ids = [(4, cls.product_product_conf_chair_floor_protect.id)]

        cls.custom_pricelist = cls.env['product.pricelist'].create({
            'name': 'Custom pricelist (TEST)',
            'sequence': 4,
            'item_ids': [(0, 0, {
                'base': 'list_price',
                'applied_on': '1_product',
                'product_tmpl_id': cls.product_product_custo_desk.id,
                'price_discount': 20,
                'min_quantity': 2,
                'compute_price': 'formula'
            })]
        })

    @classmethod
    def _create_pricelist(cls, pricelists):
        for pricelist in pricelists:
            if not pricelist.item_ids.filtered(lambda i: i.product_tmpl_id == cls.product_product_custo_desk and i.price_discount == 20):
                cls.env['product.pricelist.item'].create({
                    'base': 'list_price',
                    'applied_on': '1_product',
                    'pricelist_id': pricelist.id,
                    'product_tmpl_id': cls.product_product_custo_desk.id,
                    'price_discount': 20,
                    'min_quantity': 2,
                    'compute_price': 'formula',
                })
            pricelist.discount_policy = 'without_discount'

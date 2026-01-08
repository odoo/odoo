# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.sale.tests.common import SaleCommon


class GelatoCommon(SaleCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.gelato_template = cls.env['product.template'].create({
            'name': 'Gelato Product Template'
        })
        cls.gelato_product = cls.env['product.product'].create({
            'name': 'Test Gelato Product',
            'gelato_product_uid': 'dummy_uid',
        })
        cls.gelato_order = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'order_line': [
                Command.create({'product_id': cls.gelato_product.id, 'product_uom_qty': 1})
            ],
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

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.tests.common import WebsiteSaleCommon


class WebsiteSaleStockCommon(WebsiteSaleCommon):

    @classmethod
    def _add_product_qty_to_wh(cls, product_id, qty, loc_id):
        cls.env['stock.quant'].with_context(inventory_mode=True).create({
            'product_id': product_id,
            'inventory_quantity': qty,
            'location_id': loc_id,
        }).action_apply_inventory()

    @classmethod
    def _create_product(cls, **create_values):
        # Override of `website_sale`
        create_values['is_storable'] = True
        create_values['allow_out_of_stock_order'] = False
        return super()._create_product(**create_values)

    @classmethod
    def _create_warehouse(cls, **kwargs):
        return cls.env['stock.warehouse'].create({
            'name': 'Test Warehouse',
            'code': 'TWH',
            **kwargs,
        })

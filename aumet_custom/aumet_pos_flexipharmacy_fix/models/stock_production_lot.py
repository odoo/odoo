from datetime import datetime

from odoo import models


class StockProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    def product_lot_and_serial(self, product_id, picking_type):
        picking_type_id = self.env['stock.picking.type'].browse(picking_type)
        domain = [('product_id', '=', product_id)]
        product_expiry_module_id = self.env['ir.module.module'].sudo().search([('name', '=', 'product_expiry')])
        if product_expiry_module_id.state == 'installed':
            domain += ('|', ('expiration_date', '>', datetime.utcnow().date().strftime("%Y-%m-%d")),
                       ('expiration_date', '=', False))
        lot_ids = self.env['stock.production.lot'].search_read(domain)
        for lot_id in lot_ids:
            quant_ids = self.env['stock.quant'].search([('id', 'in', lot_id.get('quant_ids')), (
                'location_id', '=', picking_type_id.default_location_src_id.id), ('on_hand', '=', True)])
            if quant_ids and quant_ids.quantity >= 0:
                lot_id.update({
                    'location_product_qty': round(quant_ids.quantity, 3)
                })
            else:
                lot_id.update({
                    'location_product_qty': 0
                })
        return lot_ids

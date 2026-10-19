from odoo import models


class StockWarehouseOrderpoint(models.Model):
    _inherit = 'stock.warehouse.orderpoint'

    def _quantity_in_progress(self):
        res = super()._quantity_in_progress()
        draft_mo = self.env['mrp.production'].search([
            ('product_id', 'in', self.product_id.ids),
            ('state', '=', 'draft'),
            ('sale_line_id', '!=', False),
        ])
        production_group = draft_mo.grouped(lambda mo: (mo.product_id, mo.location_dest_id))
        for orderpoint in self:
            productions = production_group.get((orderpoint.product_id, orderpoint.location_id))
            if not productions:
                continue
            res[orderpoint.id] += sum(productions.mapped('product_qty'))

        return res

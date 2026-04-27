from odoo import models


class StockPickingBatch(models.Model):
    _inherit = 'stock.picking.batch'

    def action_picking_map_view(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id('stock_fleet_enterprise.stock_picking_action_view_map')
        action['domain'] = [('id', 'in', self.picking_ids.ids)]
        return action

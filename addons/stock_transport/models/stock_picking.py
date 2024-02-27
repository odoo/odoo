# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    def action_batch(self):
        domain = []
        if self._context.get('open_view') == 'tree,form':
            domain = [('state', '=', 'done')]
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Batch Transfers',
            'res_model': 'stock.picking.batch',
            'view_mode': self._context.get('open_view'),
            'target': 'current',
        }

        if domain:
            action['domain'] = domain

        return action


class StockPicking(models.Model):
    _inherit = "stock.picking"

    sequence = fields.Integer(string='Sequence')
    zip_code = fields.Char(string="Zip", related='partner_id.zip')
    max_weight = fields.Float(string="Max Weight", compute='_compute_total_weight', store=True)
    max_volume = fields.Float(string="Max Volume", compute='_compute_total_volume', store=True)

    @api.depends('move_ids.product_id.weight')
    def _compute_total_weight(self):
        for picking in self:
            max_weight = sum((move.product_qty * move.product_id.weight) or 0.0 for move in picking.move_ids)
            picking.max_weight = max_weight

    @api.depends('move_ids.product_id.volume')
    def _compute_total_volume(self):
        for picking in self:
            max_volume = sum((move.product_qty * move.product_id.volume) or 0.0 for move in picking.move_ids)
            picking.max_volume = max_volume

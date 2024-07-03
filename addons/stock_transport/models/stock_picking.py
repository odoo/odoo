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

    sequence = fields.Integer(string='Sequence', compute='update_sequence', store=True, readonly=False)
    zip_code = fields.Char(string="Zip", related='partner_id.zip')
    weight = fields.Float(string="Max Weight", compute='_compute_total_weight')
    volume = fields.Float(string="Max Volume", compute='_compute_total_volume')

    @api.depends('partner_id')
    def update_sequence(self):
        sorted_records = self.batch_id.picking_ids.filtered(lambda x: not x.partner_id or '0').sorted(key=lambda r: r.zip_code or '0')
        for idx, record in enumerate(sorted_records):
            record.sequence = idx

    @api.depends('move_ids.product_id.weight')
    def _compute_total_weight(self):
        for picking in self:
            max_weight = sum((move.product_qty * move.product_id.weight) or 0.0 for move in picking.move_ids)
            picking.weight = max_weight

    @api.depends('move_ids.product_id.volume')
    def _compute_total_volume(self):
        for picking in self:
            max_volume = sum((move.product_qty * move.product_id.volume) or 0.0 for move in picking.move_ids)
            picking.volume = max_volume

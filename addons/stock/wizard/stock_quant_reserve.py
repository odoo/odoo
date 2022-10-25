from odoo import _, api, Command, fields, models
from odoo.exceptions import UserError


class ReserveStockQuantLine(models.TransientModel):
    _name = 'stock.quant.reserve.line'
    _description = 'Choose quantity to reserve from each stock quant'

    quant_id = fields.Many2one('stock.quant', required=True, readonly=True)
    location_id = fields.Many2one(related='quant_id.location_id')
    product_id = fields.Many2one(related='quant_id.product_id')
    product_uom_id = fields.Many2one(related='product_id.uom_id')
    lot_id = fields.Many2one(related='quant_id.lot_id')
    package_id = fields.Many2one(related='quant_id.package_id')
    available_quantity = fields.Float(related='quant_id.available_quantity', string='Available')
    qty_to_reserve = fields.Float('To reserve')

    reserve_id = fields.Many2one('stock.quant.reserve')


class ReserveStockQuant(models.TransientModel):
    _name = 'stock.quant.reserve'
    _description = 'Manually reserve stock'

    move_id = fields.Many2one('stock.move')
    product_tracking = fields.Selection(related='move_id.has_tracking')
    product_uom_id = fields.Many2one(related='move_id.product_id.uom_id', readonly=True)
    demand_qty = fields.Float(compute='_compute_demand_qty', store=True)
    qty_to_reserve = fields.Float('Quantity to reserve', compute='_compute_qty_to_reserve')
    quant_line_ids = fields.One2many('stock.quant.reserve.line', 'reserve_id', compute='_compute_quant_line_ids',
                                     readonly=False, store=True)

    @api.depends('quant_line_ids.qty_to_reserve', 'demand_qty')
    def _compute_qty_to_reserve(self):
        for wiz in self:
            wiz.qty_to_reserve = max(wiz.demand_qty - sum(wiz.quant_line_ids.mapped('qty_to_reserve')), 0)

    @api.depends('move_id')
    def _compute_demand_qty(self):
        for wiz in self:
            wiz.demand_qty = wiz.move_id.product_qty - sum(wiz.move_id.move_line_ids.mapped('reserved_qty'))

    @api.depends('move_id')
    def _compute_quant_line_ids(self):
        for wiz in self:
            move_id = wiz.move_id
            if not move_id:
                wiz.quant_line_ids = False
                continue
            if wiz.quant_line_ids:
                continue
            quant_line_cmds = [Command.clear()]
            quant_ids = self.env['stock.quant'].search([('product_id', '=', move_id.product_id.id),
                                                        ('location_id', 'child_of', move_id.location_id.id)])
            quant_line_cmds += [Command.create({'quant_id': quant.id}) for quant in quant_ids.filtered(lambda q: q.available_quantity > 0)]
            wiz.quant_line_ids = quant_line_cmds

    def reserve_stock(self):
        move_line_vals = []
        for wiz in self:
            for line in wiz.quant_line_ids.filtered(lambda l: l.qty_to_reserve > 0):
                if line.qty_to_reserve > line.available_quantity:
                    raise UserError(_('Cannot reserve more quantity than available!'))
                line.quant_id.reserved_quantity += line.qty_to_reserve
                move_line_vals.append(wiz.move_id._prepare_move_line_vals(quantity=line.qty_to_reserve, reserved_quant=line.quant_id))
        StockMoveLine = self.env['stock.move.line'].with_context(bypass_reservation_update=True)
        StockMoveLine.create(move_line_vals)
        self.move_id._recompute_state()

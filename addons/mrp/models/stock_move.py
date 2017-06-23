# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round
from odoo.addons import decimal_precision as dp


class StockPackOperation(models.Model):
    _inherit = 'stock.pack.operation'

    workorder_id = fields.Many2one('mrp.workorder', 'Work Order')
    production_id = fields.Many2one('mrp.production', 'Production Order')
    lot_produced_id = fields.Many2one('stock.production.lot', 'Finished Lot')
    lot_produced_qty = fields.Float('Quantity Finished Product', help="Informative, not used in matching")
    done_wo = fields.Boolean('Done for Work Order', default=True, help="Technical Field which is False when temporarily filled in in work order")  # TDE FIXME: naming
    done_move = fields.Boolean('Move Done', related='move_id.is_done', store=True)  # TDE FIXME: naming

    @api.one
    @api.constrains('lot_id', 'qty_done')
    def _check_lot_id(self):
        if self.move_id.product_id.tracking == 'serial':
            lots = set([])
            for move_lot in self.move_id.active_move_line_ids.filtered(lambda r: not r.lot_produced_id and r.lot_id):
                if move_lot.lot_id in lots:
                    raise exceptions.UserError(_('You cannot use the same serial number in two different lines.'))
                if float_compare(move_lot.qty_done, 1.0, precision_rounding=move_lot.move_id.product_id.uom_id.rounding) == 1:
                    raise exceptions.UserError(_('You can only produce 1.0 %s for products with unique serial number.') % move_lot.product_id.uom_id.name)
                lots.add(move_lot.lot_id)

    @api.multi
    def write(self, vals):
        if 'lot_id' in vals:
            for movelot in self:
                movelot.move_id.production_id.move_raw_ids.mapped('pack_operation_ids')\
                    .filtered(lambda r: r.done_wo and not r.done_move and r.lot_produced_id == movelot.lot_id)\
                    .write({'lot_produced_id': vals['lot_id']})
        return super(StockPackOperation, self).write(vals)


class StockMove(models.Model):
    _inherit = 'stock.move'

    production_id = fields.Many2one(
        'mrp.production', 'Production Order for finished products')
    raw_material_production_id = fields.Many2one(
        'mrp.production', 'Production Order for raw materials')
    unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Unbuild Order')
    consume_unbuild_id = fields.Many2one(
        'mrp.unbuild', 'Consume Unbuild Order')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Operation To Consume')  # TDE FIXME: naming
    workorder_id = fields.Many2one(
        'mrp.workorder', 'Work Order To Consume')
    # Quantities to process, in normalized UoMs
    active_move_line_ids = fields.One2many('stock.pack.operation', 'move_id', domain=[('done_wo', '=', True)], string='Lots')
    bom_line_id = fields.Many2one('mrp.bom.line', 'BoM Line')
    unit_factor = fields.Float('Unit Factor')
    is_done = fields.Boolean(
        'Done', compute='_compute_is_done',
        store=True,
        help='Technical Field to order moves')
    
    def _get_move_lines(self):
        self.ensure_one()
        if self.raw_material_production_id:
            return self.active_move_line_ids
        else:
            return super(StockMove, self)._get_move_lines()

    @api.multi
    @api.depends('state')
    def _compute_is_done(self):
        for move in self:
            move.is_done = (move.state in ('done', 'cancel'))

    @api.multi
    def action_assign(self):
        res = super(StockMove, self).action_assign()
        for move in self.filtered(lambda x: x.production_id or x.raw_material_production_id):
            if move.pack_operation_ids:
                move.pack_operation_ids.write({'production_id': move.raw_material_production_id.id, 
                                               'workorder_id': move.workorder_id.id,})
        return res

    @api.multi
    def action_cancel(self):
        if any(move.quantity_done for move in self): #TODO: either put in stock, or check there is a production order related to it
            raise exceptions.UserError(_('You cannot cancel a stock move having already consumed material'))
        return super(StockMove, self).action_cancel()

    @api.multi
    # Could use split_move_operation from stock here
    def split_move_lot(self):
        ctx = dict(self.env.context)
        self.ensure_one()
        view = self.env.ref('mrp.view_stock_move_lots')
        serial = (self.has_tracking == 'serial')
        only_create = False  # Check operation type in theory
        show_reserved = any([x for x in self.pack_operation_ids if x.product_qty > 0.0])
        ctx.update({
            'serial': serial,
            'only_create': only_create,
            'create_lots': True,
            'state_done': self.is_done,
            'show_reserved': show_reserved,
        })
        if ctx.get('w_production'):
            action = self.env.ref('mrp.act_mrp_product_produce').read()[0]
            action['context'] = ctx
            return action
        result = {
            'name': _('Register Lots'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.move',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.id,
            'context': ctx,
        }
        return result

    @api.multi
    def save(self):
        return True

    @api.multi
    def action_confirm(self):
        moves = self.env['stock.move']
        for move in self:
            moves |= move.action_explode()
        # we go further with the list of ids potentially changed by action_explode
        return super(StockMove, moves).action_confirm()

    def action_explode(self):
        """ Explodes pickings """
        # in order to explode a move, we must have a picking_type_id on that move because otherwise the move
        # won't be assigned to a picking and it would be weird to explode a move into several if they aren't
        # all grouped in the same picking.
        if not self.picking_type_id:
            return self
        bom = self.env['mrp.bom'].sudo()._bom_find(product=self.product_id)
        if not bom or bom.type != 'phantom':
            return self
        phantom_moves = self.env['stock.move']
        processed_moves = self.env['stock.move']
        factor = self.product_uom._compute_quantity(self.product_uom_qty, bom.product_uom_id) / bom.product_qty
        boms, lines = bom.sudo().explode(self.product_id, factor, picking_type=bom.picking_type_id)
        for bom_line, line_data in lines:
            phantom_moves += self._generate_move_phantom(bom_line, line_data['qty'])

        for new_move in phantom_moves:
            processed_moves |= new_move.action_explode()
#         if not self.split_from and self.procurement_id:
#             # Check if procurements have been made to wait for
#             moves = self.procurement_id.move_ids
#             if len(moves) == 1:
#                 self.procurement_id.write({'state': 'done'})
        if processed_moves and self.state == 'assigned':
            # Set the state of resulting moves according to 'assigned' as the original move is assigned
            processed_moves.write({'state': 'assigned'})
        # delete the move with original product which is not relevant anymore
        self.sudo().unlink()
        return processed_moves

    def _generate_move_phantom(self, bom_line, quantity):
        if bom_line.product_id.type in ['product', 'consu']:
            return self.copy(default={
                'picking_id': self.picking_id.id if self.picking_id else False,
                'product_id': bom_line.product_id.id,
                'product_uom': bom_line.product_uom_id.id,
                'product_uom_qty': quantity,
                'state': 'draft',  # will be confirmed below
                'name': self.name,
                'procurement_id': self.procurement_id.id,
            })
        return self.env['stock.move']

class PushedFlow(models.Model):
    _inherit = "stock.location.path"

    def _prepare_move_copy_values(self, move_to_copy, new_date):
        new_move_vals = super(PushedFlow, self)._prepare_move_copy_values(move_to_copy, new_date)
        new_move_vals['production_id'] = False

        return new_move_vals

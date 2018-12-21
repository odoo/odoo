# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare

class MrpProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _description = "Record Production"
    _inherit = ["mrp.abstract.workorder"]

    @api.model
    def default_get(self, fields):
        res = super(MrpProductProduce, self).default_get(fields)
        if self._context and self._context.get('active_id'):
            production = self.env['mrp.production'].browse(self._context['active_id'])
            serial_finished = (production.product_id.tracking == 'serial')
            todo_uom = production.product_uom_id.id
            todo_quantity = self._get_todo(production)
            if serial_finished:
                todo_quantity = 1.0
                if production.product_uom_id.uom_type != 'reference':
                    todo_uom = self.env['uom.uom'].search([('category_id', '=', production.product_uom_id.category_id.id), ('uom_type', '=', 'reference')]).id
            if 'production_id' in fields:
                res['production_id'] = production.id
            if 'product_id' in fields:
                res['product_id'] = production.product_id.id
            if 'product_uom_id' in fields:
                res['product_uom_id'] = todo_uom
            if 'serial' in fields:
                res['serial'] = bool(serial_finished)
            if 'qty_producing' in fields:
                res['qty_producing'] = todo_quantity
        return res

    serial = fields.Boolean('Requires Serial')
    product_tracking = fields.Selection(related="product_id.tracking")
    is_pending_production = fields.Boolean(compute='_compute_pending_production')
    workorder_line_ids = fields.One2many('mrp.product.produce.line', 'workorder_id')
    move_raw_ids = fields.One2many(related='production_id.move_raw_ids')

    @api.depends('qty_producing')
    def _compute_pending_production(self):
        """ Compute if it exits remaining quantity once the quantity on the
        current wizard will be processed. The purpose is to display or not
        button 'continue'.
        """
        for product_produce in self:
            remaining_qty = product_produce._get_todo(product_produce.production_id)
            product_produce.is_pending_production = remaining_qty - product_produce.qty_producing > 0.0

    def _generate_lines_values(self, move, qty_to_consume):
        res = super(MrpProductProduce, self)._generate_lines_values(move, qty_to_consume)
        # prefill the qty done in the wizard to speed up the process
        for line in res:
            line['qty_done'] = line['qty_to_consume']
        return res

    def continue_production(self):
        """ Save current wizard and directly opens a new. """
        self.ensure_one()
        self._record_production()
        action = self.production_id.open_produce_product()
        action['context'] = {'active_id': self.production_id.id}
        return action

    def action_generate_serial(self):
        self.ensure_one()
        product_produce_wiz = self.env.ref('mrp.view_mrp_product_produce_wizard', False)
        self.final_lot_id = self.env['stock.production.lot'].create({
            'product_id': self.product_id.id
        })
        return {
            'name': _('Produce'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mrp.product.produce',
            'res_id': self.id,
            'view_id': product_produce_wiz.id,
            'target': 'new',
        }

    @api.multi
    def do_produce(self):
        """ Save the current wizard and go back to the MO. """
        self.ensure_one()
        self._record_production()
        return {'type': 'ir.actions.act_window_close'}

    def _get_todo(self, production):
        """ This method will return remaining todo quantity of production. """
        main_product_moves = production.move_finished_ids.filtered(lambda x: x.product_id.id == production.product_id.id)
        todo_quantity = production.product_qty - sum(main_product_moves.mapped('quantity_done'))
        todo_quantity = todo_quantity if (todo_quantity > 0) else 0
        return todo_quantity

    @api.multi
    def _record_production(self):
        # Nothing to do for lots since values are created using default data (stock.move.lots)
        quantity = self.qty_producing
        if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_("The production order for '%s' has no quantity specified.") % self.product_id.display_name)
        self.check_finished_move_lots()
        if self.production_id.state == 'confirmed':
            self.production_id.write({
                'date_start': datetime.now(),
            })

    @api.multi
    def check_finished_move_lots(self):
        # Update finished product moves
        self._update_finished_move(False)

        # Update components moves
        self._update_raw_moves()
        return True


class MrpProductProduceLine(models.TransientModel):
    _name = 'mrp.product.produce.line'
    _inherit = ["mrp.abstract.workorder.line"]
    _description = "Record production line"

    workorder_id = fields.Many2one('mrp.product.produce', 'Produce wizard')

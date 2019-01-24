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
    workorder_line_ids = fields.One2many('mrp.product.produce.line', 'product_produce_id')
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
        # Check all the product_produce line have a move id (the user can add product
        # to consume directly in the wizard)
        for line in self.workorder_line_ids:
            if not line.move_id:
                order = self.production_id
                # Find move_id that would match
                move_id = order.move_raw_ids.filtered(
                    lambda m: m.product_id == line.product_id and m.state not in ('done', 'cancel')
                )
                if not move_id:
                    # create a move to assign it to the line
                    move_id = self.env['stock.move'].create({
                        'name': order.name,
                        'reference': order.name,
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom_id.id,
                        'location_id': order.location_src_id.id,
                        'location_dest_id': line.product_id.property_stock_production.id,
                        'raw_material_production_id': order.id,
                        'group_id': order.procurement_group_id.id,
                        'origin': order.name,
                        'state': 'confirmed'
                    })
                line.move_id = move_id.id

        # Save product produce lines data into stock moves/move lines
        quantity = self.qty_producing
        if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_("The production order for '%s' has no quantity specified.") % self.product_id.display_name)
        self._update_finished_move()
        self._update_raw_moves()
        if self.production_id.state == 'confirmed':
            self.production_id.write({
                'date_start': datetime.now(),
            })


class MrpProductProduceLine(models.TransientModel):
    _name = 'mrp.product.produce.line'
    _inherit = ["mrp.abstract.workorder.line"]
    _description = "Record production line"

    product_produce_id = fields.Many2one('mrp.product.produce', 'Produce wizard')

    def _get_final_lot(self):
        return self.product_produce_id.final_lot_id

    def _get_production(self):
        return self.product_produce_id.production_id

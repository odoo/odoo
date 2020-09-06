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
        production = self.env['mrp.production']
        production_id = self.env.context.get('default_production_id') or self.env.context.get('active_id')
        if production_id:
            production = self.env['mrp.production'].browse(production_id)
        if production.exists():
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
            if 'consumption' in fields:
                res['consumption'] = production.bom_id.consumption
        return res

    serial = fields.Boolean('Requires Serial')
    product_tracking = fields.Selection(related="product_id.tracking")
    is_pending_production = fields.Boolean(compute='_compute_pending_production')

    move_raw_ids = fields.One2many(related='production_id.move_raw_ids', string="PO Components")
    move_finished_ids = fields.One2many(related='production_id.move_finished_ids')

    raw_workorder_line_ids = fields.One2many('mrp.product.produce.line',
        'raw_product_produce_id', string='Components')
    finished_workorder_line_ids = fields.One2many('mrp.product.produce.line',
        'finished_product_produce_id', string='By-products')
    production_id = fields.Many2one('mrp.production', 'Manufacturing Order',
        required=True, ondelete='cascade')

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
        action['context'] = {'default_production_id': self.production_id.id}
        return action

    def action_generate_serial(self):
        self.ensure_one()
        product_produce_wiz = self.env.ref('mrp.view_mrp_product_produce_wizard', False)
        self.finished_lot_id = self.env['stock.production.lot'].create({
            'product_id': self.product_id.id,
            'company_id': self.production_id.company_id.id
        })
        return {
            'name': _('Produce'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mrp.product.produce',
            'res_id': self.id,
            'view_id': product_produce_wiz.id,
            'target': 'new',
        }

    def do_produce(self):
        """ Save the current wizard and go back to the MO. """
        self.ensure_one()
        self._record_production()
        self._check_company()
        return {'type': 'ir.actions.act_window_close'}

    def _get_todo(self, production):
        """ This method will return remaining todo quantity of production. """
        main_product_moves = production.move_finished_ids.filtered(lambda x: x.product_id.id == production.product_id.id)
        todo_quantity = production.product_qty - sum(main_product_moves.mapped('quantity_done'))
        todo_quantity = todo_quantity if (todo_quantity > 0) else 0
        return todo_quantity

    def _record_production(self):
        # Check all the product_produce line have a move id (the user can add product
        # to consume directly in the wizard)
        for line in self._workorder_line_ids():
            if not line.move_id:
                # Find move_id that would match
                if line.raw_product_produce_id:
                    moves = self.move_raw_ids
                else:
                    moves = self.move_finished_ids
                move_id = moves.filtered(lambda m: m.product_id == line.product_id and m.state not in ('done', 'cancel'))
                if not move_id:
                    # create a move to assign it to the line
                    if line.raw_product_produce_id:
                        values = {
                            'name': self.production_id.name,
                            'reference': self.production_id.name,
                            'product_id': line.product_id.id,
                            'product_uom': line.product_uom_id.id,
                            'location_id': self.production_id.location_src_id.id,
                            'location_dest_id': self.product_id.property_stock_production.id,
                            'raw_material_production_id': self.production_id.id,
                            'group_id': self.production_id.procurement_group_id.id,
                            'origin': self.production_id.name,
                            'state': 'confirmed',
                            'company_id': self.production_id.company_id.id,
                        }
                    else:
                        values = self.production_id._get_finished_move_value(line.product_id.id, 0, line.product_uom_id.id)
                    move_id = self.env['stock.move'].create(values)
                line.move_id = move_id.id

        # because of an ORM limitation (fields on transient models are not
        # recomputed by updates in non-transient models), the related fields on
        # this model are not recomputed by the creations above
        self.invalidate_cache(['move_raw_ids', 'move_finished_ids'])

        # Save product produce lines data into stock moves/move lines
        quantity = self.qty_producing
        if float_compare(quantity, 0, precision_rounding=self.product_uom_id.rounding) <= 0:
            raise UserError(_("The production order for '%s' has no quantity specified.") % self.product_id.display_name)
        self._update_finished_move()
        self._update_moves()
        if self.production_id.state == 'confirmed':
            self.production_id.write({
                'date_start': datetime.now(),
            })


class MrpProductProduceLine(models.TransientModel):
    _name = 'mrp.product.produce.line'
    _inherit = ["mrp.abstract.workorder.line"]
    _description = "Record production line"

    raw_product_produce_id = fields.Many2one('mrp.product.produce', 'Component in Produce wizard')
    finished_product_produce_id = fields.Many2one('mrp.product.produce', 'Finished Product in Produce wizard')

    @api.model
    def _get_raw_workorder_inverse_name(self):
        return 'raw_product_produce_id'

    @api.model
    def _get_finished_workoder_inverse_name(self):
        return 'finished_product_produce_id'

    def _get_final_lots(self):
        product_produce_id = self.raw_product_produce_id or self.finished_product_produce_id
        return product_produce_id.finished_lot_id | product_produce_id.finished_workorder_line_ids.mapped('lot_id')

    def _get_production(self):
        product_produce_id = self.raw_product_produce_id or self.finished_product_produce_id
        return product_produce_id.production_id

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare


class MrpImmediateProductionLine(models.TransientModel):
    _name = 'mrp.immediate.production.line'
    _description = 'Immediate Production Line'

    immediate_production_id = fields.Many2one('mrp.immediate.production', 'Immediate Production', required=True)
    production_id = fields.Many2one('mrp.production', 'Production', required=True)
    to_immediate = fields.Boolean('To Process')


class MrpImmediateProduction(models.TransientModel):
    _name = 'mrp.immediate.production'
    _description = 'Immediate Production'

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if 'immediate_production_line_ids' in fields:
            if self.env.context.get('default_mo_ids'):
                res['mo_ids'] = self.env.context['default_mo_ids']
                res['immediate_production_line_ids'] = [(0, 0, {'to_immediate': True, 'production_id': mo_id[1]}) for mo_id in res['mo_ids']]
        return res

    mo_ids = fields.Many2many('mrp.production', 'mrp_production_production_rel')
    show_productions = fields.Boolean(compute='_compute_show_production')
    immediate_production_line_ids = fields.One2many(
        'mrp.immediate.production.line',
        'immediate_production_id',
        string="Immediate Production Lines")

    @api.depends('immediate_production_line_ids')
    def _compute_show_production(self):
        for wizard in self:
            wizard.show_productions = len(wizard.immediate_production_line_ids.production_id) > 1

    def process(self):
        productions_to_do = self.env['mrp.production']
        productions_not_to_do = self.env['mrp.production']
        for line in self.immediate_production_line_ids:
            if line.to_immediate is True:
                productions_to_do |= line.production_id
            else:
                productions_not_to_do |= line.production_id

        for production in productions_to_do:
            error_msg = ""
            if production.product_tracking in ('lot', 'serial') and not production.lot_producing_id:
                production.action_generate_serial()
            if production.product_tracking == 'serial' and float_compare(production.qty_producing, 1, precision_rounding=production.product_uom_id.rounding) == 1:
                production.qty_producing = 1
            else:
                production.qty_producing = production.product_qty - production.qty_produced
            production._set_qty_producing()
            for move in production.move_raw_ids.filtered(lambda m: m.state not in ['done', 'cancel']):
                rounding = move.product_uom.rounding
                for move_line in move.move_line_ids:
                    if move_line.product_uom_qty:
                        move_line.qty_done = min(move_line.product_uom_qty, move_line.move_id.should_consume_qty)
                    if float_compare(move.quantity_done, move.should_consume_qty, precision_rounding=rounding) >= 0:
                        break
                if float_compare(move.product_uom_qty, move.quantity_done, precision_rounding=move.product_uom.rounding) == 1:
                    if move.has_tracking in ('serial', 'lot'):
                        error_msg += "\n  - %s" % move.product_id.display_name

            if error_msg:
                error_msg = _('You need to supply Lot/Serial Number for products:') + error_msg
                raise UserError(error_msg)

        productions_to_validate = self.env.context.get('button_mark_done_production_ids')
        if productions_to_validate:
            productions_to_validate = self.env['mrp.production'].browse(productions_to_validate)
            productions_to_validate = productions_to_validate - productions_not_to_do
            return productions_to_validate.with_context(skip_immediate=True).button_mark_done()
        return True


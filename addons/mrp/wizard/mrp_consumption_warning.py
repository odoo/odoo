# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models, api
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_round


class MrpConsumptionWarning(models.TransientModel):
    _name = 'mrp.consumption.warning'
    _description = "Wizard in case of consumption in warning/strict and more component has been used for a MO (related to the bom)"

    mrp_production_ids = fields.Many2many('mrp.production')
    mrp_production_count = fields.Integer(compute="_compute_mrp_production_count")

    consumption = fields.Selection([
        ('flexible', 'Allowed'),
        ('warning', 'Allowed with warning'),
        ('strict', 'Blocked')], compute="_compute_consumption")
    mrp_consumption_warning_line_ids = fields.One2many('mrp.consumption.warning.line', 'mrp_consumption_warning_id')

    @api.depends("mrp_production_ids")
    def _compute_mrp_production_count(self):
        for wizard in self:
            wizard.mrp_production_count = len(wizard.mrp_production_ids)

    @api.depends("mrp_consumption_warning_line_ids.consumption")
    def _compute_consumption(self):
        for wizard in self:
            consumption_map = set(wizard.mrp_consumption_warning_line_ids.mapped("consumption"))
            wizard.consumption = "strict" in consumption_map and "strict" or "warning" in consumption_map and "warning" or "flexible"

    def action_confirm(self):
        ctx = dict(self.env.context)
        ctx.pop('default_mrp_production_ids', None)
        return self.mrp_production_ids.with_context(ctx, skip_consumption=True).button_mark_done()

    def action_set_qty(self):
        self.mrp_production_ids.action_assign()
        for production in self.mrp_production_ids:
            for move in production.move_raw_ids:
                rounding = move.product_uom.rounding
                for line in self.mrp_consumption_warning_line_ids:
                    if line.product_id != move.product_id:
                        continue
                    if float_compare(line.product_expected_qty_uom, move.product_uom_qty, precision_rounding=rounding) != 0:
                        move.product_uom_qty = line.product_uom_id._compute_quantity(line.product_expected_qty_uom, move.product_uom)
                if float_compare(move.quantity_done, move.should_consume_qty, precision_rounding=rounding) == 0:
                    continue
                new_qty = float_round((production.qty_producing - production.qty_produced) * move.unit_factor, precision_rounding=move.product_uom.rounding)
                if move.has_tracking in ('lot', 'serial'):
                    if not (production.use_auto_consume_components_lots and
                            float_compare(move.reserved_availability, new_qty, precision_rounding=move.product_uom.rounding) >= 0):
                        raise UserError(_('You need to supply Lot/Serial Number'))
                move.quantity_done = new_qty
        return self.action_confirm()

    def action_cancel(self):
        if self.env.context.get('from_workorder') and len(self.mrp_production_ids) == 1:
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'mrp.production',
                'views': [[self.env.ref('mrp.mrp_production_form_view').id, 'form']],
                'res_id': self.mrp_production_ids.id,
                'target': 'main',
            }

class MrpConsumptionWarningLine(models.TransientModel):
    _name = 'mrp.consumption.warning.line'
    _description = "Line of issue consumption"

    mrp_consumption_warning_id = fields.Many2one('mrp.consumption.warning', "Parent Wizard", readonly=True, required=True, ondelete="cascade")
    mrp_production_id = fields.Many2one('mrp.production', "Manufacturing Order", readonly=True, required=True, ondelete="cascade")
    consumption = fields.Selection(related="mrp_production_id.consumption")

    product_id = fields.Many2one('product.product', "Product", readonly=True, required=True)
    product_uom_id = fields.Many2one('uom.uom', "Unit of Measure", related="product_id.uom_id", readonly=True)
    product_consumed_qty_uom = fields.Float("Consumed", readonly=True)
    product_expected_qty_uom = fields.Float("To Consume", readonly=True)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class MrpConsumptionWarning(models.TransientModel):
    _name = 'mrp.consumption.warning'
    _description = "Wizard for warning about mismatching expected vs actual component consumption quantities for MOs"

    mrp_production_ids = fields.Many2many('mrp.production')
    mrp_production_count = fields.Integer(compute="_compute_mrp_production_count")

    mrp_consumption_warning_line_ids = fields.One2many('mrp.consumption.warning.line', 'mrp_consumption_warning_id')

    @api.depends("mrp_production_ids")
    def _compute_mrp_production_count(self):
        for wizard in self:
            wizard.mrp_production_count = len(wizard.mrp_production_ids)

    def action_confirm(self):
        ctx = dict(self.env.context)
        ctx.pop('default_mrp_production_ids', None)
        return self.mrp_production_ids.with_context(ctx, skip_consumption=True).button_mark_done()

    def action_set_qty(self):
        existing_moves_lines = self.mrp_consumption_warning_line_ids.filtered('move_id')
        for production in self.mrp_production_ids:
            for line in existing_moves_lines:
                if line.mrp_production_id != production:
                    continue
                line.move_id.quantity = line.product_expected_qty_uom
                line.move_id.picked = True
        self.env['stock.move'].create([{
            'product_id': line.product_id.id,
            'uom_id': (line.uom_id or line.product_id.uom_id).id,
            'product_uom_qty': line.product_expected_qty_uom,
            'quantity': line.product_expected_qty_uom,
            'raw_material_production_id': line.mrp_production_id.id,
            'additional': True,
            'picked': True,
        } for line in self.mrp_consumption_warning_line_ids - existing_moves_lines])
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

    product_id = fields.Many2one('product.product', "Product", readonly=True, required=True)
    uom_id = fields.Many2one('uom.uom', "Unit", readonly=True)
    product_consumed_qty_uom = fields.Float("Consumed", readonly=True)
    product_expected_qty_uom = fields.Float("To Consume", readonly=True)
    move_id = fields.Many2one('stock.move', readonly=True)

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models, api
from odoo.exceptions import UserError


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
        missing_move_vals = []
        problem_tracked_products = self.env['product.product']
        for production in self.mrp_production_ids:
            for line in self.mrp_consumption_warning_line_ids:
                if line.mrp_production_id != production:
                    continue
                for move in production.move_raw_ids:
                    if line.product_id != move.product_id:
                        continue
                    qty_expected = line.product_uom_id._compute_quantity(line.product_expected_qty_uom, move.product_uom)
                    qty_compare_result = move.product_uom.compare(qty_expected, move.quantity)
                    if qty_compare_result != 0:
                        move.quantity = qty_expected
                    # move should be set to picked to correctly consume the product
                    move.picked = True
                    # in case multiple lines with same product => set others to 0 since we have no way to know how to distribute the qty done
                    line.product_expected_qty_uom = 0
                # move was deleted before confirming MO or force deleted somehow
                if not line.product_uom_id.is_zero(line.product_expected_qty_uom):
                    missing_move_vals.append({
                        'product_id': line.product_id.id,
                        'product_uom': line.product_uom_id.id,
                        'product_uom_qty': line.product_expected_qty_uom,
                        'quantity': line.product_expected_qty_uom,
                        'raw_material_production_id': line.mrp_production_id.id,
                        'additional': True,
                        'picked': True,
                    })
        if problem_tracked_products:
            products_list = "".join(f"\n- {product_name}" for product_name in problem_tracked_products.mapped("name"))
            raise UserError(
                _(
                    "Values cannot be set and validated because a Lot/Serial Number needs to be specified for a tracked product that is having its consumed amount increased:%(products)s",
                    products=products_list,
                ),
            )
        if missing_move_vals:
            self.env['stock.move'].create(missing_move_vals)
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
    product_uom_id = fields.Many2one('uom.uom', "Unit", related="product_id.uom_id", readonly=True)
    product_consumed_qty_uom = fields.Float("Consumed", readonly=True)
    product_expected_qty_uom = fields.Float("To Consume", readonly=True)

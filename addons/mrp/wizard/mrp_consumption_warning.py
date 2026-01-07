from odoo import api, fields, models


class MrpConsumptionWarning(models.TransientModel):
    _name = 'mrp.consumption.warning'
    _description = "Wizard in case of consumption in warning/strict and more component has been used for a MO (related to the bom)"

    mrp_production_ids = fields.Many2many('mrp.production')
    mrp_production_count = fields.Integer(compute="_compute_mrp_production_count")

    consumption = fields.Selection([
        ('flexible', 'Allowed'),
        ('warning', 'Allowed with warning'),
        ('strict', 'Blocked')], compute="_compute_consumption")
    inconsistent_move_ids = fields.Many2many('stock.move', readonly=True, required=True)

    @api.depends("mrp_production_ids")
    def _compute_mrp_production_count(self):
        for wizard in self:
            wizard.mrp_production_count = len(wizard.mrp_production_ids)

    @api.depends('inconsistent_move_ids.raw_material_production_id.consumption')
    def _compute_consumption(self):
        for wizard in self:
            consumption_map = set(wizard.inconsistent_move_ids.raw_material_production_id.mapped('consumption'))
            wizard.consumption = "strict" in consumption_map and "strict" or "warning" in consumption_map and "warning" or "flexible"

    def action_confirm(self):
        ctx = dict(self.env.context)
        ctx.pop('default_mrp_production_ids', None)
        return self.mrp_production_ids.with_context(ctx, skip_consumption=True).button_mark_done()

    def action_set_qty(self):
        for order in self.mrp_production_ids:
            for move in self.inconsistent_move_ids:
                if move.raw_material_production_id == order:
                    move.quantity = move.expected_qty
                    move.picked = True
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

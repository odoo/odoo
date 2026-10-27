# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class MrpProductionForecast(models.TransientModel):
    _name = 'mrp.production.forecast'
    _description = "Preview Forecast Wizard"

    production_id = fields.Many2one('mrp.production', 'Manufacturing Order', readonly=True)
    uom_id = fields.Many2one('uom.uom', 'Product UoM', compute="_compute_infos")
    ready_to_produce = fields.Float("Ready to Produce", compute="_compute_infos", digits='Product Unit', readonly=True)
    forecasted = fields.Float("Forecasted", compute="_compute_infos", digits='Product Unit', readonly=True)

    @api.depends('production_id')
    def _compute_infos(self):
        for wizard in self:
            report_values = self.env['report.mrp.report_bom_structure']._get_report_data(bom_id=wizard.production_id.bom_id.id)
            wizard.uom_id = report_values['lines']['product'].uom_id
            wizard.ready_to_produce = report_values["lines"]["uom"]._compute_quantity(report_values["lines"]["producible_qty"], wizard.uom_id, round=False)
            wizard.forecasted = wizard.production_id.product_id.virtual_available

    def action_view_forecast(self):
        self.ensure_one()
        return self.production_id.action_product_forecast_report()

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from json import dumps
from dateutil.relativedelta import relativedelta


from odoo import api, fields, models
from odoo.tools import format_date


class BomLeadTimeInfo(models.TransientModel):
    _name = 'mrp.bom.replenishment.info'
    _description = 'Bom lead time information'

    product_id = fields.Many2one('product.product')
    route_id = fields.Many2one('stock.route')
    json_lead_days = fields.Char(compute='_compute_json_lead_days')

    warehouse_id = fields.Many2one('stock.warehouse')

    @api.depends('product_id', 'warehouse_id')
    def _compute_json_lead_days(self):
        self.json_lead_days = False
        for blti in self:
            if not blti.product_id:
                continue
            values, description = self.env['stock.rule'].search([('route_id', '=', blti.route_id.id), ('warehouse_id', '=', blti.warehouse_id.id)])._get_lead_days(blti.product_id)
            blti.json_lead_days = dumps({
                'lead_days_date': format_date(self.env, fields.Date.today() + relativedelta(days=values['total_delay'])),
                'lead_days_description': description,
                'today': format_date(self.env, fields.Date.today())
            })

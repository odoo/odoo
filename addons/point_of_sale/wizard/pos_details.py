# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import UserError


class PosDetails(models.TransientModel):
    _name = 'pos.details.wizard'
    _description = 'Open Sale Details Report'

    start_date = fields.Datetime(required=True, default=fields.Datetime.now)
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)
    pos_config_ids = fields.Many2many('pos.config', 'pos_detail_configs',
        default=lambda s: s.env['pos.config'].search([]))

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    @api.multi
    def generate_report(self):
        ctx = self.env.context.copy()
        data = {'date_start': self.start_date, 'date_stop': self.end_date}
        ctx.update(data)
        return self.env['report'].with_context(ctx).get_action(
            [], 'point_of_sale.report_saledetails', data=data)

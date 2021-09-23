# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from datetime import timedelta


class PosDetails(models.TransientModel):
    _name = 'pos.details.wizard'
    _description = 'Point of Sale Details Report'

    def _default_start_date(self):
        """ Find the earliest start_date of the latests sessions """
        values = self.env["pos.session"].read_group([
            ('config_id', 'in', self.env['pos.config']._search([])),
            ('start_at', '>', fields.Datetime.now() - timedelta(days=2))
        ], ["start_at:max", "config_id"], ["config_id"])
        latest_start_dates = [res['start_at'] for res in values]
        # earliest of the latest sessions
        return latest_start_dates and min(latest_start_dates) or fields.Datetime.now()

    start_date = fields.Datetime(required=True, default=_default_start_date)
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

    def generate_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'config_ids': self.pos_config_ids.ids}
        return self.env.ref('point_of_sale.sale_details_report').report_action([], data=data)

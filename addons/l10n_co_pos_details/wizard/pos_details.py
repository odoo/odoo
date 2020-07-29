# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

from odoo import api, fields, models


class PosDetails(models.TransientModel):
    _name = 'l10n_co_pos.details.wizard'

    start_date = fields.Datetime(required=True, default=lambda x: fields.Datetime.now() - timedelta(days=2))
    end_date = fields.Datetime(required=True, default=fields.Datetime.now)
    include_products = fields.Boolean()
    pos_config_id = fields.Many2one('pos.config', required=True)

    @api.onchange('start_date')
    def _onchange_start_date(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            self.end_date = self.start_date

    @api.onchange('end_date')
    def _onchange_end_date(self):
        if self.end_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    def generate_co_pos_report(self):
        data = {
            'date_start': self.start_date,
            'date_stop': self.end_date,
            'config_ids': self.pos_config_id.ids,
            'include_products': self.include_products
        }
        return self.env.ref('l10n_co_pos_details.sale_details_report').report_action([], data=data)

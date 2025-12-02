# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models


class PosDetailsWizard(models.TransientModel):
    _name = 'pos.details.wizard'
    _description = 'Point of Sale Details Report'

    def _default_start_date(self):
        """ Find the earliest start_date of the latests sessions """
        values = self.env['pos.session']._read_group([
            ('config_id', '!=', False),
            ('start_at', '>', self.env.cr.now() - timedelta(days=2))
        ], groupby=['config_id'], aggregates=['start_at:max'])
        mapping = dict(values)
        return (mapping and min(mapping.values())) or self.env.cr.now()

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
        if self.end_date and self.start_date and self.end_date < self.start_date:
            self.start_date = self.end_date

    def generate_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'config_ids': self.pos_config_ids.ids}
        return self.env.ref('point_of_sale.sale_details_report').report_action([], data=data)

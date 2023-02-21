# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PosDailyReport(models.TransientModel):
    _name = 'pos.daily.sales.reports.wizard'
    _description = 'Point of Sale Daily Report'

    pos_session_id = fields.Many2one('pos.session')

    def generate_report(self):
        data = {'date_start': False, 'date_stop': False, 'config_ids': self.pos_session_id.config_id.ids, 'session_ids': self.pos_session_id.ids}
        return self.env.ref('point_of_sale.sale_details_report').report_action([], data=data)

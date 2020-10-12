# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosDetails(models.TransientModel):
    _inherit = 'pos.details.wizard'
    _description = 'Point of Sale Details Report'

    include_products = fields.Boolean(string="Include Product in Report")
    country_code = fields.Char(default=lambda self: self.env.company.country_id.code)
    config_len = fields.Integer()

    @api.onchange('pos_config_ids')
    def oncahnge_pos_config_ids(self):
        self.config_len = len(self.pos_config_ids)

    def generate_report(self):
        data = {
            'date_start': self.start_date,
            'date_stop': self.end_date,
            'config_ids': self.pos_config_ids.ids,
            'include_products': self.include_products if self.country_code == 'CO' and self.config_len == 1 else True}
        return self.env.ref('point_of_sale.sale_details_report').report_action([], data=data)

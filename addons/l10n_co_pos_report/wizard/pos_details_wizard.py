# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError


class PosDetails(models.TransientModel):
    _inherit = 'pos.details.wizard'
    _description = 'Point of Sale Details Report'

    include_products = fields.Boolean(string="Include Product in Report")
    country_code = fields.Char(default=lambda self: self.env.company.country_id.code)

    def generate_report(self):
        data = {'date_start': self.start_date, 'date_stop': self.end_date, 'config_ids': self.pos_config_ids.ids, 'include_products': self.include_products}
        if self.country_code == 'CO' and any(code != 'CO' for code in self.pos_config_ids.mapped('company_id.country_id.code')):
            raise UserError(_("You are trying to Print non Colombian company's report from Colombian company."))
        elif self.country_code == 'CO':
            return self.env.ref('l10n_co_pos_report.sale_details_report').report_action([], data=data)
        return self.env.ref('point_of_sale.sale_details_report').report_action([], data=data)

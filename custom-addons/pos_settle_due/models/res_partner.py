# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    def get_total_due(self, pos_currency):
        if self.env.company.currency_id.id != pos_currency:
            pos_currency = self.env['res.currency'].browse(pos_currency)
            return self.env.company.currency_id._convert(self.total_due, pos_currency, self.env.company, fields.Date.today())
        return self.total_due

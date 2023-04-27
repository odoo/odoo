# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class IrConfigParameter(models.Model):
    _inherit = 'ir.config_parameter'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('key') in ['mail.bounce.alias', 'mail.catchall.alias']:
                vals['value'] = self.env['mail.alias']._clean_and_check_unique(vals.get('value'))
        return super().create(vals_list)

    def write(self, vals):
        for parameter in self:
            if 'value' in vals and parameter.key in ['mail.bounce.alias', 'mail.catchall.alias'] and vals['value'] != parameter.value:
                vals['value'] = self.env['mail.alias']._clean_and_check_unique(vals.get('value'))
        return super().write(vals)

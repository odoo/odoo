
# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class L10nKeItemCode(models.Model):
    _name = 'l10n_ke.item.code'
    _description = "KRA defined codes that justify a given tax rate / exemption"
    _rec_names_search = ['code', 'description']

    code = fields.Char(string='KRA Item Code')
    description = fields.Char(string='Description')
    tax_rate = fields.Selection([('C', 'Zero Rated'), ('E', 'Exempted'), ('B', 'Taxable at 8%')])

    @api.depends('code', 'description')
    def _compute_display_name(self):
        for item_code in self:
            item_code.display_name = f'{item_code.code} {item_code.description}'

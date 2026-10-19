# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class L10n_ItDdt(models.Model):
    _name = 'l10n_it.ddt'
    _description = 'Transport Document'

    invoice_id = fields.One2many('account.move', 'l10n_it_ddt_id', string='Invoice Reference')
    name = fields.Char(string="Numero DDT", size=20, help="Transport document number", required=True)
    date = fields.Date(string="Data DDT", help="Transport document date", required=True)

    @api.depends('date')
    def _compute_display_name(self):
        for ddt in self:
            ddt.display_name = f"{ddt.name} ({ddt.date})"

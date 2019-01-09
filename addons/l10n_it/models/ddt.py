# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api

class L10nItDdt(models.Model):
    _name = 'l10n.it.ddt'
    _description = 'Transport Document'

    l10n_it_invoice_id = fields.One2many('account.invoice', 'l10n_it_ddt_id', string='Invoice Reference',
                                 ondelete='cascade')

    l10n_it_name = fields.Char(string="Numero DDT", size=20, help="Transport document number", required=True)
    l10n_it_date = fields.Date(string="Data DDT", help="Transport document date", required=True)

    @api.multi
    def name_get(self):
        res = []
        for ddt in self:
            res.append((ddt.id, ("%s (%s)") % (ddt.l10n_it_name, ddt.l10n_it_date)))
        return res

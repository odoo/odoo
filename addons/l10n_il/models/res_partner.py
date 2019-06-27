# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    l10n_il_income_tax_id_number = fields.Char(string='IncomeTax ID')
    l10n_il_registry_number = fields.Char(string='Registry Number')
    l10n_il_withh_tax_reason = fields.Selection([('06', 'Payments'), ('07', 'Payments to a foreign person or a foreign company done by an Israeli enterprise'), ('18', 'Dividend payments')], required=True, default='06', string='WHT Reason', readonly=False)

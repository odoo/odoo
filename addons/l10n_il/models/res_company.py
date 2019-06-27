# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _description = 'Companies'
    _inherit = 'res.company'

    l10n_il_company_income_tax_id_number = fields.Char(string='IncomeTax ID', readonly=False)
    l10n_il_withh_tax_id_number = fields.Char(string='WHT ID', readonly=False)

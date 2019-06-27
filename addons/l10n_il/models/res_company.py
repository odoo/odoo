# -*- coding: utf-8 -*-

from odoo import fields, models


class ResCompany(models.Model):
    _name = 'res.company'
    _description = 'Companies'
    _inherit = 'res.company'

    l10n_il_income_tax_id_number = fields.Char(string='IncomeTax ID', related="partner_id.l10n_il_income_tax_id_number", readonly=False)
    l10n_il_registry_number = fields.Char(string='Registry Number',  related="partner_id.l10n_il_registry_number", readonly=False)
    l10n_il_withh_tax_id_number = fields.Char(string='WHT ID', readonly=False)

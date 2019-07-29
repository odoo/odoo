# -*- coding: utf-8 -*-

from odoo import fields, models


class ResPartner(models.Model):
    _name = 'res.partner'
    _inherit = 'res.partner'

    l10n_il_income_tax_id_number = fields.Char(string='IncomeTax ID')
    l10n_il_registry_number = fields.Char(string='Registry Number')

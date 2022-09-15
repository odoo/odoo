# coding: utf-8
from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_nl_oin = fields.Char(string='Organisatie Indentificatie Nummer')

# coding: utf-8
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_nl_kvk = fields.Char(related='partner_id.l10n_nl_kvk', readonly=False)
    l10n_nl_oin = fields.Char(related='partner_id.l10n_nl_oin', readonly=False)

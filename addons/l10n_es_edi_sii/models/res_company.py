# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_es_edi_tax_agency = fields.Selection(
        string="Tax Agency for SII",
        selection=[
            ('aeat', "Agencia Tributaria española"),
            ('gipuzkoa', "Hacienda Foral de Gipuzkoa"),
            ('bizkaia', "Hacienda Foral de Bizkaia"),
        ],
        default=False,
    )

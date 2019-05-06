# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models


class AfipIncoterm(models.Model):

    _name = 'l10n_ar.afip.incoterm'
    _description = 'AFIP Incoterm'

    afip_code = fields.Char(
        'Code',
        required=True
    )
    name = fields.Char(
        required=True
    )

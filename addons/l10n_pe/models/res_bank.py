from odoo import fields, models
from odoo.addons import base


class ResBank(models.Model, base.ResBank):

    l10n_pe_edi_code = fields.Char(
        'Code (PE)',
        help='Bank code assigned by the SUNAT to identify banking institutions.')
    country_code = fields.Char(related='country.code', string='Country Code')

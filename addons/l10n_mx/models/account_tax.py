# coding: utf-8
from odoo import models, fields


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_mx_tax_type = fields.Selection(
        selection=[
            ('Tasa', "Tasa"),
            ('Cuota', "Cuota"),
            ('Exento', "Exento"),
        ],
        string="Factor Type",
        default='Tasa',
        help="The CFDI version 3.3 have the attribute 'TipoFactor' in the tax lines. In it is indicated the factor "
             "type that is applied to the base of the tax.")

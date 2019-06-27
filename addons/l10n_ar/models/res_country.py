# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCountry(models.Model):

    _inherit = 'res.country'

    l10n_ar_afip_code = fields.Char(
        'AFIP Code', size=3, help='This code will be used on electronic invoice and citi reports')

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ResCountry(models.Model):

    _inherit = 'res.country'

    l10n_ar_afip_code = fields.Char('AFIP Code', size=3, help='This code will be used on electronic invoice')
    l10n_ar_natural_vat = fields.Char(
        'Natural Person VAT', size=11, help="Generic VAT number defined by AFIP in order to recognize partners from"
        " this country that are natural persons")
    l10n_ar_legal_entity_vat = fields.Char(
        'Legal Entity VAT', size=11, help="Generic VAT number defined by AFIP in order to recognize partners from this"
        " country that are legal entity")
    l10n_ar_other_vat = fields.Char(
        'Other VAT', size=11, help="Generic VAT number defined by AFIP in order to recognize partners from this"
        " country that are not natural persons or legal entities")

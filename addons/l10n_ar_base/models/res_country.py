# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class ResCountry(models.Model):

    _inherit = 'res.country'

    l10n_ar_cuit_fisica = fields.Char(
        'CUIT Natural Person', size=11, help="CUIT defined by AFIP in order to"
        " recognize partners from this country that are natural persons")
    l10n_ar_cuit_juridica = fields.Char(
        'CUIT Legal Entity', size=11, help="CUIT defined by AFIP in order to"
        " recognize partners from this country that are legal entity")
    l10n_ar_cuit_otro = fields.Char(
        'CUIT Other', size=11, help="CUIT defined by AFIP in order to"
        " recognize partners from this country that are not natural persons"
        " or legal entity, maybe some other type of person category")

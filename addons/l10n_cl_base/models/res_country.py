# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, fields, models


class ResCountry(models.Model):
    _name = 'res.country'
    _inherit = 'res.country'

    l10n_cl_customs_name = fields.Char('Customs Name')
    l10n_cl_customs_code = fields.Char('Customs Name')
    l10n_cl_customs_abbreviation = fields.Char('Customs Name')

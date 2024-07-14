# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class l10nChLppInsurance(models.Model):
    _inherit = 'l10n.ch.lpp.insurance'

    insurance_company = fields.Char(required=True)
    insurance_code = fields.Char(required=True)

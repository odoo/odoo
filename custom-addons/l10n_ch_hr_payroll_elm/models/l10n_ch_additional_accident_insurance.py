# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class l10nChAdditionalAccidentInsurance(models.Model):
    _inherit = "l10n.ch.additional.accident.insurance"

    insurance_company = fields.Char(required=True, store=True)
    insurance_code = fields.Char(required=True, store=True, compute=False)

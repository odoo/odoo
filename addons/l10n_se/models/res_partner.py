# Part of Odoo. See LICENSE file for full copyright and licensing details.

from stdnum import luhn
from stdnum.exceptions import ValidationError as StdnumValidationError

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_se_check_vendor_ocr = fields.Boolean(string='Check Vendor OCR', help='This Vendor uses OCR Number on their Vendor Bills.')
    l10n_se_default_vendor_payment_ref = fields.Char(string='Default Vendor Payment Ref', help='If set, the vendor uses the same Default Payment Reference or OCR Number on all their Vendor Bills.')

    @api.onchange('l10n_se_default_vendor_payment_ref', 'l10n_se_check_vendor_ocr')
    def _onchange_l10n_se_default_vendor_payment_ref(self):
        if self.l10n_se_default_vendor_payment_ref and self.l10n_se_check_vendor_ocr:
            try:
                luhn.validate(self.l10n_se_default_vendor_payment_ref)
            except StdnumValidationError:
                return {'warning': {'title': self.env._('Warning'), 'message': self.env._("Default vendor OCR number isn't a valid OCR number.")}}
        return None

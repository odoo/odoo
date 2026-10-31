# Part of Odoo. See LICENSE file for full copyright and licensing details.

from stdnum import luhn
from stdnum.exceptions import ValidationError as StdnumValidationError

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_se_check_vendor_ocr = fields.Boolean(string='Check Vendor OCR', help='This Vendor uses OCR Number on their Vendor Bills.')
    l10n_se_default_vendor_payment_ref = fields.Char(string='Default Vendor Payment Ref', help='If set, the vendor uses the same Default Payment Reference or OCR Number on all their Vendor Bills.')
    l10n_se_sni_ids = fields.One2many(comodel_name='l10n_se.partner.sni', inverse_name='partner_id', string='SNI Codes')
    l10n_se_primary_sni_id = fields.Many2one(comodel_name='l10n_se.sni', string='Primary SNI Code', compute='_compute_primary_sni', store=True, help='The SNI code with the lowest sequence number on the company.')

    @api.onchange('l10n_se_default_vendor_payment_ref', 'l10n_se_check_vendor_ocr')
    def _onchange_l10n_se_default_vendor_payment_ref(self):
        if self.l10n_se_default_vendor_payment_ref and self.l10n_se_check_vendor_ocr:
            try:
                luhn.validate(self.l10n_se_default_vendor_payment_ref)
            except StdnumValidationError:
                return {'warning': {'title': self.env._('Warning'), 'message': self.env._("Default vendor OCR number isn't a valid OCR number.")}}
        return None

    @api.depends(
        'commercial_partner_id.l10n_se_sni_ids',
        'commercial_partner_id.l10n_se_sni_ids.sequence',
        'commercial_partner_id.l10n_se_sni_ids.sni_id',
    )
    def _compute_primary_sni(self):
        """Primary SNI code of the company: the assignment with the lowest sequence.

        SNI codes are kept on the commercial partner (the company); its contacts
        get the same primary code.
        """
        for partner in self:
            first = partner.commercial_partner_id.l10n_se_sni_ids[:1]
            partner.l10n_se_primary_sni_id = first.sni_id if first else False

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from stdnum import luhn


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_se_check_vendor_ocr = fields.Boolean(string='Check Vendor OCR', help='This Vendor uses OCR Number on their Vendor Bills.')
    l10n_se_default_vendor_payment_ref = fields.Char(string='Default Vendor Payment Ref', help='If set, the vendor uses the same Default Payment Reference or OCR Number on all their Vendor Bills.')

    @api.onchange('l10n_se_default_vendor_payment_ref')
    def onchange_l10n_se_default_vendor_payment_ref(self):
        if not self.l10n_se_default_vendor_payment_ref == "" and self.l10n_se_check_vendor_ocr:
            reference = self.l10n_se_default_vendor_payment_ref
            try:
                luhn.validate(reference)
            except: 
                return {'warning': {'title': _('Warning'), 'message': _('Default vendor OCR number isn\'t a valid OCR number.')}}

    @api.depends('vat', 'country_id')
    def _compute_company_registry(self):
        # OVERRIDE
        # If a swedish company has a VAT number then its company registry is its VAT Number (without country code and last 2 digits).
        super()._compute_company_registry()
        for partner in self:
            if partner._deduce_country_code() != 'SE' or not partner.vat:
                continue
            vat_country, vat_number = self._split_vat(partner.vat)
            if vat_country in ('SE', '') and self._check_vat_number('SE', vat_number):
                partner.company_registry = vat_number[:-2]

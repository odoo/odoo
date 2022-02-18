# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from stdnum import luhn


class ResPartner(models.Model):
    _inherit = 'res.partner'

    l10n_se_check_vendor_ocr = fields.Boolean(string='Check Vendor OCR', help='This Vendor uses OCR Number on their Vendor Bills.')
    l10n_se_default_vendor_payment_ref = fields.Char(string='Default Vendor Payment Ref', help='If set, the vendor uses the same Default Payment Reference or OCR Number on all their Vendor Bills.')
    user_country_code = fields.Char(string="User current company country code", compute="_compute_user_country_code")

    @api.onchange('l10n_se_default_vendor_payment_ref')
    def onchange_l10n_se_default_vendor_payment_ref(self):
        if not self.l10n_se_default_vendor_payment_ref == "" and self.l10n_se_check_vendor_ocr:
            reference = self.l10n_se_default_vendor_payment_ref
            try:
                luhn.validate(reference)
            except: 
                return {'warning': {'title': _('Warning'), 'message': _('Default vendor OCR number isn\'t a valid OCR number.')}}

    @api.depends_context("allowed_company_ids")
    def _compute_user_country_code(self):
        cid = self._context.get("allowed_company_ids", [None])[0]
        self.user_country_code = self.env["res.company"].browse(cid).country_code if cid else "SE"

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        if self.session_id.company_id.country_id.code == 'IN':
            partner = self.partner_id
            l10n_in_gst_treatment = partner.l10n_in_gst_treatment
            if not l10n_in_gst_treatment and partner.country_id and partner.country_id.code != 'IN':
                l10n_in_gst_treatment = 'overseas'
            if not l10n_in_gst_treatment:
                l10n_in_gst_treatment = partner.vat and 'regular' or 'consumer'
            vals['l10n_in_gst_treatment'] = l10n_in_gst_treatment
        return vals

    def _prepare_product_aml_dict(self, base_line_vals, update_base_line_vals, rate, sign):
        res = super()._prepare_product_aml_dict(base_line_vals, update_base_line_vals, rate, sign)
        if self.company_id.account_fiscal_country_id.code == 'IN':
            res.update({
                'l10n_in_hsn_code': base_line_vals['l10n_in_hsn_code'],
            })
        return res

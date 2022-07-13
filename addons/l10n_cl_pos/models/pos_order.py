# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def _order_fields(self, ui_order):
        fields = super()._order_fields(ui_order)
        order_company = self.env['pos.session'].browse(ui_order['pos_session_id']).company_id
        if order_company.country_id.code == 'CL':
            if not fields['partner_id']:
                fields['partner_id'] = self.env.ref('l10n_cl.par_cfa').id
        return fields

    def _prepare_invoice_vals(self):
        vals = super()._prepare_invoice_vals()
        has_tax = bool(self.lines.tax_ids)
        if self.to_invoice and self.partner_id.country_id.code != 'CL' and \
                self.partner_id.l10n_cl_sii_taxpayer_type == '4':
            vals['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_fe_dte').id
        elif self.to_invoice and self.partner_id.l10n_cl_sii_taxpayer_type in ['1', '2']:
            if has_tax:
                vals['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_a_f_dte').id
            else:
                vals['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_y_f_dte').id
        else:
            if has_tax:
                vals['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_b_f_dte').id
            else:
                vals['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_b_e_dtn').id
        return vals

    def _should_create_invoice(self):
        res = super()._should_create_invoice()
        if self.company_id.country_id.code == 'CL':
            res = res or self.state == 'paid'
        return res

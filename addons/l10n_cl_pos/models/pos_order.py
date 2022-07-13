# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models



# Manage taxes or not (done)
# Manage refund
# type export for foreigners => boleta if end customer, exportation if foreigner

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
        if self.company_id.country_id.code == 'CL':
            has_tax = bool(self.lines.tax_ids)
            if self.partner_id.country_id.code != 'CL':
                if self.partner_id.l10n_cl_sii_taxpayer_type == '3':
                    if has_tax:
                        vals['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_b_f_dte').id
                    else:
                        vals['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_b_e_dtn').id
                else:
                    vals['l10n_latam_document_type_id'] = self.env.ref('l10n_cl.dc_fe_dte').id
            else:
                if self.to_invoice:
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
        res = vals = super()._should_create_invoice()
        if self.company_id.country_id.code == 'CL':
            res = res or self.state == 'paid'
        return res

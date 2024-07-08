# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    module_l10n_in_edi = fields.Boolean('Indian Electronic Invoicing')
    module_l10n_in_edi_ewaybill = fields.Boolean('Indian Electronic Waybill')
    l10n_in_hsn_code_digit = fields.Selection(related='company_id.l10n_in_hsn_code_digit', readonly=False)
    module_l10n_in_tds = fields.Boolean(related='company_id.module_l10n_in_tds', readonly=False, string='TDS')
    module_l10n_in_tcs = fields.Boolean(related='company_id.module_l10n_in_tcs', readonly=False, string='TCS')
    module_accountant = fields.Boolean()
    l10n_in_gst = fields.Boolean(related='company_id.l10n_in_gst', readonly=False)
    module_l10n_in_reports = fields.Boolean()

    @api.onchange('module_l10n_in_tds', 'module_l10n_in_tcs', 'l10n_in_gst')
    def _onchange_l10n_in_tds_tcs_gst(self):
        warnings = {
            'module_l10n_in_tds': _("Once TDS is enabled, it cannot be disabled."),
            'module_l10n_in_tcs': _("Once TCS is enabled, it cannot be disabled."),
            'l10n_in_gst': _("Once GST is enabled, it cannot be disabled."),
        }
        company = self.env.company
        fields_to_check = ['module_l10n_in_tds', 'module_l10n_in_tcs', 'l10n_in_gst']
        for field in fields_to_check:
            if self.country_code == 'IN' and not company[field] and self[field]:
                return {
                    'warning': {
                        'title': _("Warning"),
                        'message': warnings[field]
                    }
                }

    @api.model
    def set_values(self):
        res = super().set_values()
        self._update_gst_tax_active_state()
        return res

    def _update_gst_tax_active_state(self):
        if self.l10n_in_gst:
            tax_group_refs = [
                'sgst_group',
                'cgst_group',
                'igst_group',
                'cess_group',
                'gst_group',
                'exempt_group',
                'nil_rated_group',
                'non_gst_supplies_group',
            ]
            tax_group_ids = [self.env['account.chart.template'].ref(group_ref).id for group_ref in tax_group_refs]
            taxes = self.env['account.tax'].search([('tax_group_id', 'in', tax_group_ids)])
            taxes.write({'active': True})

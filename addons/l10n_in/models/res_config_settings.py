# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError, RedirectWarning
from odoo.addons.l10n_in.models.iap_account import IAP_SERVICE_NAME


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    l10n_in_edi_production_env = fields.Boolean(
        string="Indian Production Environment",
        related="company_id.l10n_in_edi_production_env",
        readonly=False
    )
    l10n_in_hsn_code_digit = fields.Selection(related='company_id.l10n_in_hsn_code_digit', readonly=False)

    # TDS/TCS settings
    l10n_in_tds_feature = fields.Boolean(related='company_id.l10n_in_tds_feature', readonly=False)
    l10n_in_tcs_feature = fields.Boolean(related='company_id.l10n_in_tcs_feature', readonly=False)
    l10n_in_withholding_account_id = fields.Many2one(related='company_id.l10n_in_withholding_account_id', readonly=False)
    l10n_in_withholding_journal_id = fields.Many2one(related='company_id.l10n_in_withholding_journal_id', readonly=False)
    l10n_in_tan = fields.Char(related='company_id.l10n_in_tan', readonly=False)

    # GST settings
    l10n_in_is_gst_registered = fields.Boolean(related='company_id.l10n_in_is_gst_registered', readonly=False)
    l10n_in_gstin = fields.Char(string="GST Number", related='company_id.vat', readonly=False)
    l10n_in_gstin_status_feature = fields.Boolean(related='company_id.l10n_in_gstin_status_feature', readonly=False)
    l10n_in_gst_efiling_feature = fields.Boolean(related='company_id.l10n_in_gst_efiling_feature', readonly=False)
    l10n_in_fetch_vendor_edi_feature = fields.Boolean(related='company_id.l10n_in_fetch_vendor_edi_feature', readonly=False)
    # Automatically set to True if either l10n_in_gst_efiling_feature or l10n_in_fetch_vendor_edi_feature is activated.
    module_l10n_in_reports = fields.Boolean('GST E-Filing & Matching')

    # E-Invoice
    l10n_in_edi_feature = fields.Boolean(related='company_id.l10n_in_edi_feature', readonly=False)
    # Automatically set to True if l10n_in_edi_feature is activated.
    module_l10n_in_edi = fields.Boolean('Indian Electronic Invoicing')

    # E-Waybill
    l10n_in_ewaybill_feature = fields.Boolean(related='company_id.l10n_in_ewaybill_feature', readonly=False)
    # Automatically set to True if l10n_in_ewaybill_feature is activated.
    module_l10n_in_ewaybill = fields.Boolean('Indian Electronic Waybill')

    # ENet Batch Payment
    l10n_in_enet_vendor_batch_payment_feature = fields.Boolean(related='company_id.l10n_in_enet_vendor_batch_payment_feature', readonly=False)

    def set_values(self):
        super().set_values()
        if self.country_code == 'IN':
            if not self.module_l10n_in_reports and (self.l10n_in_fetch_vendor_edi_feature or self.l10n_in_gst_efiling_feature or self.l10n_in_enet_vendor_batch_payment_feature):
                self.module_l10n_in_reports = True
            if not self.module_l10n_in_edi and self.l10n_in_edi_feature:
                self.module_l10n_in_edi = True
            if not self.module_l10n_in_ewaybill and self.l10n_in_ewaybill_feature:
                self.module_l10n_in_ewaybill = True

    def l10n_in_edi_buy_iap(self):
        if not self.l10n_in_edi_production_env or not (self.l10n_in_edi_feature or self.l10n_in_gstin_status_feature or self.l10n_in_ewaybill_feature or self.l10n_in_gst_efiling_feature):
            raise ValidationError(_(
                "Please ensure that at least one Indian service and production environment is enabled,"
                " and save the configuration to proceed with purchasing credits."
            ))
        return {
            'type': 'ir.actions.act_url',
            'url': self.env["iap.account"].get_credits_url(service_name=IAP_SERVICE_NAME),
            'target': '_new'
        }

    def _l10n_in_check_gst_number(self):
        if not self.company_id.vat:
            action = {
                'view_mode': 'form',
                'res_model': 'res.company',
                'type': 'ir.actions.act_window',
                'res_id': self.company_id.id,
                'views': [[self.env.ref('base.view_company_form').id, 'form']],
            }
            raise RedirectWarning(_("Please enter a GST number in company."), action, _("Go to Company"))

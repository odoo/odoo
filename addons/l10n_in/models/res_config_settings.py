# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError, RedirectWarning
from odoo.addons.l10n_in.models.iap_account import IAP_SERVICE_NAME
from odoo.tools.sql import column_exists, create_column
from odoo.tools import SQL


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

    # GST settings
    l10n_in_is_gst_registered = fields.Boolean(related='company_id.l10n_in_is_gst_registered', readonly=False)
    l10n_in_gstin = fields.Char(string="GST Number", related='company_id.vat', readonly=False)
    l10n_in_gstin_status_feature = fields.Boolean(related='company_id.l10n_in_gstin_status_feature', readonly=False)
    l10n_in_gst_efiling_feature = fields.Boolean(string="GST E-Filing & Matching Feature")
    l10n_in_fetch_vendor_edi_feature = fields.Boolean(string="Fetch Vendor E-Invoiced Document")
    l10n_in_enet_vendor_batch_payment_feature = fields.Boolean(string="ENet Vendor Batch Payment")

    module_l10n_in_reports = fields.Boolean('GST E-Filing & Matching')
    module_l10n_in_edi = fields.Boolean('Indian Electronic Invoicing')
    module_l10n_in_ewaybill = fields.Boolean('Indian Electronic Waybill')

    def set_values(self):
        super().set_values()
        if self.country_code == 'IN':
            if not self.module_l10n_in_reports and (self.l10n_in_fetch_vendor_edi_feature or self.l10n_in_gst_efiling_feature or self.l10n_in_enet_vendor_batch_payment_feature):
                self.module_l10n_in_reports = True
            if self.l10n_in_fetch_vendor_edi_feature:
                self._update_l10n_in_feature("l10n_in_fetch_vendor_edi_feature")
            if self.l10n_in_gst_efiling_feature:
                self._update_l10n_in_feature("l10n_in_gst_efiling_feature")
            if self.l10n_in_enet_vendor_batch_payment_feature:
                self._update_l10n_in_feature("l10n_in_enet_vendor_batch_payment_feature")
            if self.module_l10n_in_edi:
                self._update_l10n_in_feature("l10n_in_edi_feature")
            if self.module_l10n_in_ewaybill:
                self._update_l10n_in_feature("l10n_in_ewaybill_feature")

    def _update_l10n_in_feature(self, column):
        """ This way, after installing the module, the field will already be set for the active company. """
        if not column_exists(self.env.cr, "res_company", column):
            create_column(self.env.cr, "res_company", column, "boolean")
            self.env.cr.execute(SQL(
                f"""
                    UPDATE res_company
                    SET {column} = true
                    WHERE id = {self.env.company.id}
                """
            ))

    def l10n_in_edi_buy_iap(self):
        if not self.l10n_in_edi_production_env or not (self.module_l10n_in_edi or self.module_l10n_in_ewaybill or self.l10n_in_gstin_status_feature or self.l10n_in_gst_efiling_feature):
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

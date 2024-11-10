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
    module_l10n_in_edi = fields.Boolean('Indian Electronic Invoicing')
    module_l10n_in_ewaybill = fields.Boolean('Indian Electronic Waybill')
    module_l10n_in_gstin_status = fields.Boolean('Check GST Number Status')
    l10n_in_tcs = fields.Boolean(related='company_id.l10n_in_tcs', readonly=False)
    l10n_in_tds = fields.Boolean(related='company_id.l10n_in_tds', readonly=False)
    l10n_in_hsn_code_digit = fields.Selection(related='company_id.l10n_in_hsn_code_digit', readonly=False)
    module_l10n_in_enet_batch_payment = fields.Boolean(string="Vendor Payment")
    module_l10n_in_reports_gstr = fields.Boolean(string="GST E-Filing & Matching")
    module_l10n_in_gst_api = fields.Boolean(string="Fetch Vendor E-Invoiced Document")
    l10n_in_tan = fields.Char(related='company_id.l10n_in_tan', readonly=False)
    l10n_in_is_gst_registered = fields.Boolean(related='company_id.l10n_in_is_gst_registered', readonly=False)
    l10n_in_gstin = fields.Char(string="GST Number", related='company_id.vat', readonly=False)

    def l10n_in_edi_buy_iap(self):
        if not self.l10n_in_edi_production_env or not (self.module_l10n_in_edi or self.module_l10n_in_gstin_status or self.module_l10n_in_reports_gstr):
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

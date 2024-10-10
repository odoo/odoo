# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import ValidationError, UserError
from odoo.tools.misc import str2bool
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
    module_l10n_in_edi_ewaybill = fields.Boolean('Indian Electronic Waybill')
    module_l10n_in_gstin_status = fields.Boolean('Check GST Number Status')
    module_l10n_in_withholding = fields.Boolean('Indian TDS and TCS')
    module_l10n_in_reports_gstr = fields.Boolean('GSTR India eFiling')
    l10n_in_hsn_code_digit = fields.Selection(related='company_id.l10n_in_hsn_code_digit', readonly=False)
    module_l10n_in_enet_batch_payment = fields.Boolean(string="Vendor Payment")
    l10n_in_is_gst_registered = fields.Boolean('Register Under GST', config_parameter='l10n_in.l10n_in_is_gst_registered')
    l10n_in_gstin = fields.Char(related='company_id.vat', readonly=False)
    l10n_in_tax_payer_type = fields.Selection(
        selection=[
            ('normal_taxpayer', 'Normal Taxpayer'),
            ('composition_taxpayer', 'Composition Taxpayer'),
            ('casual_taxable_person', 'Casual Taxable Person'),
            ('input_service_distributor', 'Input Service Distributor (ISD)'),
            ('non_resident_taxable_person', 'Non-Resident Taxable Person'),
            ('online_service_distributor', 'Non-Resident Online Service Distributor'),
            ('embassy_un_body', 'Embassy / UN Body / Other Notified Persons'),
            ('sez_developer_unit', 'Special Economic Zone (SEZ) Developer / Unit'),
            ('tds_tcs', 'Tax Deductor at Source (TDS) / Tax Collector at Source (TCS)'),
        ],
        string='Payer Type',
        config_parameter='l10n_in.l10n_in_tax_payer_type'
    )
    l10n_in_tan = fields.Char(related='company_id.l10n_in_tan', readonly=False)

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

    def set_values(self):
        if self.country_code == 'IN':
            old_value = str2bool(self.env['ir.config_parameter'].get_param('l10n_in.l10n_in_is_gst_registered'))
            if old_value != self.l10n_in_is_gst_registered:
                if old_value:
                    raise UserError(_('Once GST is enabled, it cannot be disabled.'))
                self._archive_u_r_taxes()
                self._activate_gst_taxes()
                # Set sale and purchase tax accounts when GST is enabled.
                self.company_id.account_sale_tax_id = self.env['account.chart.template'].ref('sgst_sale_5').id
                self.company_id.account_purchase_tax_id = self.env['account.chart.template'].ref('sgst_purchase_5').id
        return super().set_values()

    def _archive_u_r_taxes(self):
        taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', self.company_id.id),
            ('name', 'ilike', '% U R'),
        ])
        taxes.write({'active': False})

    def _activate_gst_taxes(self):
        taxes = self.env['account.tax'].with_context(active_test=False).search([
            ('company_id', '=', self.company_id.id),
            ('name', 'not ilike', '% U R'),
        ])
        taxes.write({'active': True})

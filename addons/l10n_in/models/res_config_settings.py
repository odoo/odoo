# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError, RedirectWarning


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    module_l10n_in_edi = fields.Boolean(string='Indian Electronic Invoicing')
    module_l10n_in_edi_ewaybill = fields.Boolean(string='Indian Electronic Waybill')
    module_l10n_in_reports_gstr = fields.Boolean(string='Indian GST Service')
    l10n_in_hsn_code_digit = fields.Selection(related='company_id.l10n_in_hsn_code_digit', readonly=False)
    l10n_in_edi_env = fields.Selection(
        string="Indian EDI Environment",
        related="company_id.l10n_in_edi_env",
        readonly=False
    )

    def l10n_in_check_gst_number(self):
        if not self.company_id.vat:
            action = {
                    "view_mode": "form",
                    "res_model": "res.company",
                    "type": "ir.actions.act_window",
                    "res_id" : self.company_id.id,
                    "views": [[self.env.ref("base.view_company_form").id, "form"]],
            }
            raise RedirectWarning(_("Please enter a GST number in company."), action, _('Go to Company'))

    def l10n_in_edi_buy_iap(self):
        if not self.l10n_in_edi_env == 'production':
            raise UserError(_("You must enable production environment to buy credits"))
        return {
            'type': 'ir.actions.act_url',
            'url': self.env["iap.account"].get_credits_url(service_name="l10n_in_edi", base_url=''),
            'target': '_new'
        }

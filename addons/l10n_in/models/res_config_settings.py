# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, fields, models
from odoo.exceptions import RedirectWarning


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    module_l10n_in_edi = fields.Boolean('Indian Electronic Invoicing')
    module_l10n_in_ewaybill = fields.Boolean('Indian Waybill')
    l10n_in_hsn_code_digit = fields.Selection(related='company_id.l10n_in_hsn_code_digit', readonly=False)

    def l10n_in_check_gst_number(self):
        if not self.company_id.vat:
            action = {
                    "view_mode": "form",
                    "res_model": "res.company",
                    "type": "ir.actions.act_window",
                    "res_id": self.company_id.id,
                    "views": [[self.env.ref("base.view_company_form").id, "form"]],
            }
            raise RedirectWarning(_("Please enter a GST number in company."), action, _('Go to Company'))

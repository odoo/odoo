# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    module_l10n_in_edi = fields.Boolean('Indian Electronic Invoicing')
    module_l10n_in_edi_ewaybill = fields.Boolean('Indian Electronic Waybill')
    l10n_in_hsn_code_digit = fields.Selection(related='company_id.l10n_in_hsn_code_digit', readonly=False)
    l10n_in_tds_toggle = fields.Boolean(related='company_id.l10n_in_tds_toggle', readonly=False)

    @api.onchange('l10n_in_tds_toggle')
    def _onchange_l10n_in_tds_toggle(self):
        if self.country_code == 'IN' and not self.env.company.l10n_in_tds_toggle and self.l10n_in_tds_toggle:
            return {'warning': {
                'title': _("Warning"),
                'message': _("Once TDS is enabled, it cannot be disabled.")
            }}

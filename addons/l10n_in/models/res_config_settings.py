# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    group_l10n_in_reseller = fields.Boolean(implied_group='l10n_in.group_l10n_in_reseller', string="Manage Reseller(E-Commerce)")
    module_l10n_in_edi = fields.Boolean(
        string='Indian Electronic Invoicing',
        related='company_id.module_l10n_in_edi',
        readonly=False
    )
    module_l10n_in_edi_ewaybill = fields.Boolean(
        string='Indian Electronic Waybill',
        related='company_id.module_l10n_in_edi_ewaybill',
        readonly=False
    )
    module_l10n_in_reports_gstr = fields.Boolean(
        string='Indian GST Service',
        related='company_id.module_l10n_in_reports_gstr',
        readonly=False
    )
    l10n_in_hsn_code_digit = fields.Selection(related='company_id.l10n_in_hsn_code_digit', readonly=False)

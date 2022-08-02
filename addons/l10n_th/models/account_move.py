# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    l10n_th_vat = fields.Char(related="partner_id.vat", string="Tax ID")
    l10n_th_company_info = fields.Selection(
        related="partner_id.l10n_th_company_info", string="Company Information")
    l10n_th_branch_number = fields.Char(
        related="partner_id.l10n_th_branch_number", string="Branch Number")
    l10n_th_custom_header = fields.Boolean("Use Custom Invoice Header")

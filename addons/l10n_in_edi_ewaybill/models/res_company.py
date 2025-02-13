# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_edi_ewaybill_username = fields.Char("E-Waybill (IN) Username", groups="base.group_system")
    l10n_in_edi_ewaybill_password = fields.Char("E-Waybill (IN) Password", groups="base.group_system")
    l10n_in_edi_ewaybill_auth_validity = fields.Datetime(
        string="E-Waybill (IN) Valid Until",
        groups="base.group_system",
        compute="_compute_l10n_in_edi_ewaybill_auth_validity",
        store=True,
    )

    @api.depends('vat', 'l10n_in_edi_ewaybill_username')
    def _compute_l10n_in_edi_ewaybill_auth_validity(self):
        self.filtered(
            lambda c: c.account_fiscal_country_id.code == 'IN' and c.l10n_in_edi_ewaybill_auth_validity
        ).sudo().l10n_in_edi_ewaybill_auth_validity = False

    def _l10n_in_edi_ewaybill_token_is_valid(self):
        self.ensure_one()
        if self.l10n_in_edi_ewaybill_auth_validity and self.l10n_in_edi_ewaybill_auth_validity > fields.Datetime.now():
            return True
        return False

    def _get_l10n_in_api_list(self):
        api_list = super()._get_l10n_in_api_list()
        api_list.append(_("e-waybill"))
        return api_list

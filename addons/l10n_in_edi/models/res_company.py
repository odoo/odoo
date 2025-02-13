# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    l10n_in_edi_username = fields.Char("E-invoice (IN) Username", groups="base.group_system")
    l10n_in_edi_password = fields.Char("E-invoice (IN) Password", groups="base.group_system")
    l10n_in_edi_token = fields.Char(
        string="E-invoice (IN) Token",
        groups="base.group_system",
        compute="_compute_l10n_in_edi_token_and_edi_token_validity",
        store=True,
    )
    l10n_in_edi_token_validity = fields.Datetime(
        string="E-invoice (IN) Valid Until",
        groups="base.group_system",
        compute="_compute_l10n_in_edi_token_and_edi_token_validity",
        store=True,
    )

    @api.depends('vat', 'l10n_in_edi_username')
    def _compute_l10n_in_edi_token_and_edi_token_validity(self):
        filtered_set = self.filtered(
            lambda c: c.account_fiscal_country_id.code == 'IN' and c.l10n_in_edi_token and c.l10n_in_edi_token_validity
        )
        filtered_set.sudo().l10n_in_edi_token = False
        filtered_set.sudo().l10n_in_edi_token_validity = False

    def _l10n_in_edi_token_is_valid(self):
        self.ensure_one()
        if self.l10n_in_edi_token and self.l10n_in_edi_token_validity > fields.Datetime.now():
            return True
        return False

    def _get_l10n_in_api_list(self):
        api_list = super()._get_l10n_in_api_list()
        api_list.append(_("e-invoice"))
        return api_list

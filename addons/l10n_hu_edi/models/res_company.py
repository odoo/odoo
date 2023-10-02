# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class ResCompany(models.Model):
    _inherit = "res.company"

    # Hungarian fields
    l10n_hu_is_vat_group_member = fields.Boolean(
        "TAX Group membership", related="partner_id.l10n_hu_is_vat_group_member", readonly=False
    )
    l10n_hu_vat_group_member = fields.Char(
        "Group Member TAX Number", related="partner_id.l10n_hu_vat_group_member", readonly=False
    )

    l10n_hu_company_tax_arrangments = fields.Selection(
        related="partner_id.l10n_hu_company_tax_arrangments", readonly=False
    )

    # TAX Authority login credentials
    l10n_hu_nav_credential_ids = fields.One2many("l10n_hu.nav_communication", "company_id", string="NAV Credentials")
    l10n_hu_production_cred = fields.Boolean(
        "Hungary: Production usage", compute="_comp_l10n_hu_in_production", compute_sudo=True
    )

    l10n_hu_use_demo_mode = fields.Boolean("Hungary: Demo mode?")

    @api.depends("vat", "l10n_hu_nav_credential_ids.username", "l10n_hu_nav_credential_ids.state")
    def _comp_l10n_hu_in_production(self):
        for company in self:
            company.l10n_hu_production_cred = bool(
                self.env["l10n_hu.nav_communication"].search_count(
                    [
                        ("company_id", "=", company.id),
                        ("state", "=", "prod"),
                    ],
                    limit=1,
                )
            )

    def _prepare_hu_demo_objects(self):
        for c in self:
            profit_account = self.env["account.account"].search(
                [
                    ("company_id", "=", c.id),
                    ("code", "=", "969000"),
                ],
                limit=1,
            )
            loss_account = self.env["account.account"].search(
                [
                    ("company_id", "=", c.id),
                    ("code", "=", "869000"),
                ],
                limit=1,
            )

            self.env["account.cash.rounding"].create(
                {
                    "name": "Kerekítés 1.00-ra",
                    "rounding": 1.0,
                    "strategy": "add_invoice_line",
                    "profit_account_id": profit_account.id,
                    "loss_account_id": loss_account.id,
                    "rounding_method": "HALF-UP",
                }
            )

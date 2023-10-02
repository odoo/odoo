# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ResPartner(models.Model):
    _inherit = "res.partner"
    _rec_names_search = ["display_name", "email", "ref", "vat", "company_registry", "l10n_hu_vat_group_member"]

    l10n_hu_is_vat_group_member = fields.Boolean(
        "TAX Group membership", default=False, help="If the company is a member of a vat group.", index=True
    )
    l10n_hu_vat_group_member = fields.Char(
        "Group Member TAX Number",
        size=13,
        copy=False,
        help="Group Membership VAT Number, if this company is a member of a Hungarian VAT group",
        index=True,
    )

    l10n_hu_company_tax_arrangments = fields.Selection(
        [
            ("ie", "Individual Exemption"),
            ("ca", "Cash Accounting"),
            ("sb", "Small Business"),
        ],
        string="Special tax arrangements",
    )

    @api.model
    def _commercial_fields(self):
        return super()._commercial_fields() + [
            "l10n_hu_is_vat_group_member",
            "l10n_hu_vat_group_member",
            "l10n_hu_company_tax_arrangments",
        ]

    @api.depends("vat", "company_id", "company_registry", "l10n_hu_is_vat_group_member", "l10n_hu_vat_group_member")
    def _compute_same_vat_partner_id(self):
        for partner in self:
            # use _origin to deal with onchange()
            partner_id = partner._origin.id
            # active_test = False because if a partner has been deactivated you still want to raise the error,
            # so that you can reactivate it instead of creating a new one, which would loose its history.
            Partner = self.with_context(active_test=False).sudo()
            domain = [
                ("vat", "=", partner.vat),
                ("l10n_hu_is_vat_group_member", "=", False),
            ]
            # So for the hungarian group VAT handling: we will alert
            # if the vat and the group vat is the same together
            if Partner.l10n_hu_is_vat_group_member:
                domain = (
                    ["|", "&"]
                    + domain
                    + [
                        "&",
                        "&",
                        ("vat", "=", partner.vat),
                        ("l10n_hu_vat_group_member", "=", partner.l10n_hu_vat_group_member),
                        ("l10n_hu_is_vat_group_member", "=", True),
                    ]
                )
            if partner.company_id:
                domain += [("company_id", "in", [False, partner.company_id.id])]
            if partner_id:
                domain += [("id", "!=", partner_id), "!", ("id", "child_of", partner_id)]
            # For VAT number being only one character, we will skip the check just like the regular check_vat
            should_check_vat = partner.vat and len(partner.vat) != 1
            partner.same_vat_partner_id = should_check_vat and not partner.parent_id and Partner.search(domain, limit=1)
            # check company_registry
            domain = [
                ("company_registry", "=", partner.company_registry),
                ("company_id", "in", [False, partner.company_id.id]),
            ]
            if partner_id:
                domain += [("id", "!=", partner_id), "!", ("id", "child_of", partner_id)]
            partner.same_company_registry_partner_id = (
                bool(partner.company_registry) and not partner.parent_id and Partner.search(domain, limit=1)
            )

    @api.model
    def _run_vies_test(self, vat_number, default_country):
        """Convert back the hungarian format to EU format: 12345678-1-12 => HU12345678"""
        if default_country and default_country.code == "HU" and not vat_number.startswith("HU"):
            vat_number = f"HU{vat_number[:8]}"
        return super()._run_vies_test(vat_number, default_country)

# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.exceptions import ValidationError

# res.partner additional identifier holding the ID number of each statutory
# privilege type (registered in res_partner.py).
PARTNER_IDENTIFIER_KEYS = {"sc": "PH_SC_ID", "pwd": "PH_PWD_ID"}


class L10nPhDiscountPrivilege(models.Model):
    _name = "l10n_ph.discount.privilege"
    _description = "Philippines Discount Privilege"
    _order = "name, id"
    _check_company_auto = True

    name = fields.Char(string="Discount Name", required=True)
    discount_type = fields.Selection(
        selection=[
            ("pwd", "PWD Discount"),
            ("sc", "Senior Citizen Discount"),
            ("special", "Special Discount"),
        ],
        string="Type",
        required=True,
        default="pwd",
    )
    discount_amount = fields.Float(
        string="Discount Amount",
        required=True,
        digits="Discount",
    )
    fiscal_position_id = fields.Many2one(
        comodel_name="account.fiscal.position",
        string="Fiscal Position",
        check_company=True,
        help="Fiscal position mapping the taxes of the invoice lines to the "
        "SC/PWD VAT-exempt taxes when the privilege is applied. The original "
        "taxes are restored when the privilege is removed. Leave empty to "
        "apply the privilege without changing the taxes.",
    )
    account_id = fields.Many2one(
        "account.account",
        string="Account",
        required=True,
        check_company=True,
    )
    applied_to_category_ids = fields.Many2many(
        "product.category",
        string="Applies To",
        help="Product categories the privilege applies to. If a parent "
        "category is selected, all of its child categories are also "
        "considered. Leave empty to apply the privilege to all products.",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    active = fields.Boolean("Active", default=True)
    l10n_ph_id_type_label = fields.Char(
        string="ID Type",
        compute="_compute_l10n_ph_id_type_label",
        help="Name of the ID document presented for this privilege.",
    )

    _l10n_ph_discount_privilege_name_company_uniq = models.Constraint(
        "unique(name, company_id)",
        "A discount privilege with this name already exists for this company.",
    )

    @api.depends("discount_type", "name")
    @api.depends_context("lang")
    def _compute_l10n_ph_id_type_label(self):
        # Statutory privileges are named after their ID document (e.g.
        # "Senior Citizen ID"); non-statutory ("special") ones after themselves.
        Partner = self.env["res.partner"]
        identifiers_metadata = Partner._get_all_additional_identifiers_metadata()
        for privilege in self:
            metadata = identifiers_metadata.get(PARTNER_IDENTIFIER_KEYS.get(privilege.discount_type), {})
            label = Partner._lazy_translate_additional_identifiers_metadata(metadata).get("label")
            privilege.l10n_ph_id_type_label = label or privilege.name

    @api.constrains("discount_amount")
    def _check_discount_amount(self):
        for privilege in self:
            if not (0 < privilege.discount_amount <= 1.0):
                raise ValidationError(
                    self.env._(
                        "Discount Amount must be greater than 0 and at most 100%.",
                    ),
                )

    def _l10n_ph_get_applied_category_ids(self):
        """
        Return the product categories the privilege applies to, including
        all their child categories (a privilege granted on a parent category
        also covers products assigned to any of its children).
        """
        self.ensure_one()
        categories = self.applied_to_category_ids
        if categories:
            categories |= self.env["product.category"].search(
                [("id", "child_of", categories.ids)],
            )
        return categories

    def _l10n_ph_get_partner_id_number(self, partner):
        """ID number of this privilege's ID document on ``partner``'s
        additional identifiers, if any."""
        self.ensure_one()
        identifier_key = PARTNER_IDENTIFIER_KEYS.get(self.discount_type)
        return identifier_key and (partner.additional_identifiers or {}).get(identifier_key)

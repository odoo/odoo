from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = "account.account"

    depreciation_profile_ids = fields.Many2many(
        comodel_name="account.depreciation.profile",
        string="Depreciation Profiles",
        tracking=True,
        help="An asset is created for each depreciation profile when this account is used on a vendor bill or a refund",
    )
    create_asset = fields.Selection(
        selection=[
            ("no", "No"),
            ("draft", "Create in draft"),
            ("validate", "Create and validate"),
        ],
        compute="_compute_create_asset",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        tracking=True,
    )
    can_create_asset = fields.Boolean(compute="_compute_can_create_asset")
    multiple_assets_per_line = fields.Boolean(
        string="Multiple Assets per Line",
        default=False,
        tracking=True,
        help="Multiple asset items will be generated depending on the bill line quantity instead of 1 global asset.",
    )

    @api.depends("account_type")
    def _compute_can_create_asset(self):
        for record in self:
            record.can_create_asset = record.account_type in (
                "asset_fixed",
                "asset_non_current",
            )

    @api.onchange("create_asset")
    def _onchange_multiple_assets_per_line(self):
        for record in self:
            if record.create_asset == "no":
                record.multiple_assets_per_line = False

    @api.depends("depreciation_profile_ids")
    def _compute_create_asset(self):
        for account in self:
            if not account.create_asset or account.create_asset == "no":
                account.create_asset = (
                    "draft" if account.depreciation_profile_ids else "no"
                )

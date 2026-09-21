from odoo import api, fields, models


class L10nInConfig(models.Model):
    _name = "l10n_in.config"
    _description = "A company's l10n in configuration"
    _inherit = ["mixin.company.config"]

    l10n_in_upi_id = fields.Char(string="UPI Id")
    l10n_in_hsn_code_digit = fields.Selection(
        selection=[
            ("4", "4 Digits (turnover < 5 CR.)"),
            ("6", "6 Digits (turnover > 5 CR.)"),
            ("8", "8 Digits"),
        ],
        string="HSN Code Digit",
        compute="_compute_l10n_in_hsn_code_digit",
        store=True,
        readonly=False,
    )
    l10n_in_edi_production_env = fields.Boolean(
        string="Indian Production Environment",
        default=True,
        groups="base.group_system",
        help="Enable the use of production credentials",
    )
    l10n_in_tds_feature = fields.Boolean(
        string="TDS",
        inverse="_inverse_l10n_in_tds_feature",
    )
    l10n_in_tcs_feature = fields.Boolean(
        string="TCS",
        inverse="_inverse_l10n_in_tcs_feature",
    )
    l10n_in_withholding_account_id = fields.Many2one(
        comodel_name="account.account",
        string="TDS Account",
        check_company=True,
    )
    l10n_in_withholding_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="TDS Journal",
        check_company=True,
    )
    l10n_in_is_gst_registered = fields.Boolean(
        string="Registered Under GST",
        inverse="_inverse_l10n_in_is_gst_registered",
    )
    l10n_in_gstin_status_feature = fields.Boolean(string="Check GST Number Status")

    def _inverse_l10n_in_is_gst_registered(self):
        for config in self:
            if config.l10n_in_is_gst_registered:
                company = config.company_id
                gst_group_refs = [
                    "sgst_group",
                    "cgst_group",
                    "igst_group",
                    "cess_group",
                    "gst_group",
                    "exempt_group",
                    "nil_rated_group",
                    "non_gst_supplies_group",
                ]
                company._activate_l10n_in_taxes(gst_group_refs, company)
                # Set sale and purchase tax accounts when user registered under GST.
                company.account_config_id.account_sale_tax_id = (
                    self.env["account.chart.template"]
                    .with_company(company)
                    .ref("sgst_sale_5", raise_if_not_found=False)
                )
                company.account_config_id.account_purchase_tax_id = (
                    self.env["account.chart.template"]
                    .with_company(company)
                    .ref("sgst_purchase_5", raise_if_not_found=False)
                )

    def _inverse_l10n_in_tds_feature(self):
        for config in self:
            if config.l10n_in_tds_feature:
                config.company_id._activate_l10n_in_taxes(
                    ["tds_group"], config.company_id
                )

    def _inverse_l10n_in_tcs_feature(self):
        for config in self:
            if config.l10n_in_tcs_feature:
                config.company_id._activate_l10n_in_taxes(
                    ["tcs_group"], config.company_id
                )

    @api.depends("company_id.vat")
    def _compute_l10n_in_hsn_code_digit(self):
        for record in self:
            if record.company_id.country_code == "IN" and record.company_id.vat:
                record.l10n_in_hsn_code_digit = "4"
            else:
                record.l10n_in_hsn_code_digit = False

    @api.model
    def _get_field_names_delegated_to_root(self):
        # a branch shares its root's TDS, TCS and GST registration: the mixin
        # defaults them from the parent and refuses a branch that disagrees,
        # where a recursive compute merely overwrote the branch in silence
        return super()._get_field_names_delegated_to_root() + [
            "l10n_in_tds_feature",
            "l10n_in_tcs_feature",
            "l10n_in_is_gst_registered",
        ]

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class L10nHrEdiConfig(models.Model):
    _name = "l10n_hr_edi.config"
    _description = "A company's l10n hr edi configuration"
    _inherit = ["mixin.company.config"]

    l10n_hr_mer_username = fields.Char(
        string="MojEracun username",
        groups="account.group_account_manager",
    )
    l10n_hr_mer_company_ident = fields.Char(
        string="MojEracun CompanyId",
        groups="account.group_account_manager",
    )
    l10n_hr_mer_software_ident = fields.Char(
        string="MojEracun SoftwareId",
        default="Saodoo-001",
        help="Default SoftwareID for Odoo is 'Saodoo-001'",
    )
    l10n_hr_mer_connection_state = fields.Selection(
        selection=[
            ("inactive", "Inactive"),
            ("active", "Active"),
        ],
        string="MojEracun connection status",
        compute="_compute_l10n_hr_mojeracun_state",
        default="inactive",
        store=True,
        required=True,
    )
    l10n_hr_mer_connection_mode = fields.Selection(
        selection=[
            ("prod", "Production"),
            ("test", "Test"),
            ("demo", "Demo"),
        ],
        string="MojEracun Operating mode",
        default="test",
    )
    l10n_hr_mer_purchase_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="eracun Purchase Journal",
        compute="_compute_l10n_hr_mer_purchase_journal_id",
        store=True,
        readonly=False,
        domain=[("type", "=", "purchase")],
        check_company=True,
    )

    # -------------------------------------------------------------------------
    # CONSTRAINTS
    # -------------------------------------------------------------------------

    @api.constrains("l10n_hr_mer_purchase_journal_id")
    def _check_l10n_hr_mer_purchase_journal_id(self):
        for config in self:
            if (
                config.l10n_hr_mer_purchase_journal_id
                and config.l10n_hr_mer_purchase_journal_id.type != "purchase"
            ):
                raise ValidationError(
                    self.env._(
                        "A purchase journal must be used to receive eRacun document via MojEracun."
                    )
                )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends("l10n_hr_mer_connection_state")
    def _compute_l10n_hr_mer_purchase_journal_id(self):
        missing = self.filtered(
            lambda config: (
                not config.l10n_hr_mer_purchase_journal_id
                and config.l10n_hr_mer_connection_state == "active"
            )
        )
        journal_by_company = missing.company_id._first_journal_per_company("purchase")
        for config in missing:
            config.l10n_hr_mer_purchase_journal_id = journal_by_company[
                config.company_id
            ]

    @api.depends("l10n_hr_mer_username", "company_id.l10n_hr_mer_password")
    def _compute_l10n_hr_mojeracun_state(self):
        for config in self:
            if not (
                config.l10n_hr_mer_username and config.company_id.l10n_hr_mer_password
            ):
                config.l10n_hr_mer_connection_state = "inactive"

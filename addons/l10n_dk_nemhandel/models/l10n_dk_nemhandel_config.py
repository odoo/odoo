from odoo import api, fields, models
from odoo.exceptions import ValidationError


class L10nDkNemhandelConfig(models.Model):
    _name = "l10n_dk_nemhandel.config"
    _description = "A company's l10n dk nemhandel configuration"
    _inherit = ["mixin.company.config"]

    nemhandel_contact_email = fields.Char(
        string="Nemhandel Contact email",
        compute="_compute_nemhandel_contact_email",
        store=True,
        readonly=False,
        help="Primary contact email for Nemhandel-related communication",
    )
    nemhandel_phone_number = fields.Char(
        string="Nemhandel Phone number (for validation)",
        compute="_compute_nemhandel_phone_number",
        store=True,
        readonly=False,
        help="You will receive a verification code to this phone number",
    )
    l10n_dk_nemhandel_proxy_state = fields.Selection(
        selection=[
            ("not_registered", "Not registered"),
            ("in_verification", "In verification"),
            ("receiver", "Can send and receive"),
            ("rejected", "Rejected"),
        ],
        string="Nemhandel status",
        default="not_registered",
        required=True,
    )
    nemhandel_purchase_journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_nemhandel_purchase_journal_id",
        store=True,
        readonly=False,
        domain=[("type", "=", "purchase")],
    )
    nemhandel_edi_user = fields.Many2one(
        comodel_name="account_edi_proxy_client.user",
        compute="_compute_nemhandel_edi_user",
    )

    @api.constrains("nemhandel_phone_number")
    def _check_nemhandel_phone_number(self):
        for config in self:
            if config.nemhandel_phone_number:
                config.company_id._normalize_nemhandel_phone_number(
                    config.nemhandel_phone_number
                )

    @api.constrains("nemhandel_purchase_journal_id")
    def _check_nemhandel_purchase_journal_id(self):
        for config in self:
            if (
                config.nemhandel_purchase_journal_id
                and config.nemhandel_purchase_journal_id.type != "purchase"
            ):
                raise ValidationError(
                    self.env._(
                        "A purchase journal must be used to receive Nemhandel documents."
                    )
                )

    @api.depends("l10n_dk_nemhandel_proxy_state")
    def _compute_nemhandel_purchase_journal_id(self):
        for config in self:
            if (
                not config.nemhandel_purchase_journal_id
                and config.l10n_dk_nemhandel_proxy_state
                not in {"not_registered", "rejected"}
            ):
                config.nemhandel_purchase_journal_id = self.env[  # noqa: E8507 - one lookup per company, on its own journals
                    "account.journal"
                ].search(
                    [
                        *self.env["account.journal"]._check_company_domain(
                            config.company_id
                        ),
                        ("type", "=", "purchase"),
                    ],
                    limit=1,
                )
                config.nemhandel_purchase_journal_id.is_nemhandel_journal = True
            else:
                config.nemhandel_purchase_journal_id = (
                    config.nemhandel_purchase_journal_id
                )

    @api.depends("company_id.email")
    def _compute_nemhandel_contact_email(self):
        for config in self:
            if not config.nemhandel_contact_email:
                config.nemhandel_contact_email = config.company_id.email

    @api.depends("company_id.phone_ids")
    def _compute_nemhandel_phone_number(self):
        for config in self:
            if not config.nemhandel_phone_number:
                company_phone = config.company_id.phone_ids._primary().number
                try:
                    # precompute only if it's a valid phone number
                    config.company_id._normalize_nemhandel_phone_number(company_phone)
                    config.nemhandel_phone_number = company_phone
                except ValidationError:
                    continue

    @api.depends("company_id.account_edi_proxy_client_ids")
    def _compute_nemhandel_edi_user(self):
        for config in self:
            config.nemhandel_edi_user = (
                config.company_id.account_edi_proxy_client_ids.filtered(
                    lambda u: u.proxy_type == "nemhandel"
                )
            )

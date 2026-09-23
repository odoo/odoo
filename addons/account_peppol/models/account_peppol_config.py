from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountPeppolConfig(models.Model):
    _name = "account_peppol.config"
    _description = "A company's account peppol configuration"
    _inherit = ["mixin.company.config"]

    account_peppol_contact_email = fields.Char(
        string="Primary contact email",
        compute="_compute_account_peppol_contact_email",
        store=True,
        readonly=False,
        help="Primary contact email for Peppol connection related communications and notifications.\n"
        "In particular, this email is used by Odoo to reconnect your Peppol account in case of database change.",
    )
    account_peppol_phone_number = fields.Char(
        string="Mobile number",
        compute="_compute_account_peppol_phone_number",
        store=True,
        readonly=False,
        help="This number is used for identification purposes only.",
    )
    account_peppol_proxy_state = fields.Selection(
        selection=[
            ("not_registered", "Not registered"),
            ("sender", "Can send but not receive"),
            ("smp_registration", "Can send, pending registration to receive"),
            ("receiver", "Can send and receive"),
            ("rejected", "Rejected"),
        ],
        string="PEPPOL status",
        default="not_registered",
        required=True,
    )
    account_peppol_edi_user = fields.Many2one(
        comodel_name="account_edi_proxy_client.user",
        compute="_compute_account_peppol_edi_user",
    )
    peppol_purchase_journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_peppol_purchase_journal_id",
        inverse="_inverse_peppol_purchase_journal_id",
        store=True,
        readonly=False,
        domain=[("type", "=", "purchase")],
    )
    peppol_external_provider = fields.Char(tracking=True)
    peppol_can_send = fields.Boolean(compute="_compute_peppol_can_send")
    peppol_parent_company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_peppol_parent_company_id",
    )
    peppol_metadata = fields.Json()
    peppol_metadata_updated_at = fields.Datetime(string="Peppol meta updated at")
    peppol_activate_self_billing_sending = fields.Boolean(
        string="Activate self-billing sending",
        help="If activated, you will be able to send vendor bills as self-billed invoices via Peppol.",
    )
    peppol_self_billing_reception_journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Self-Billing reception journal",
        compute="_compute_peppol_self_billing_reception_journal_id",
        inverse="_inverse_peppol_self_billing_reception_journal_id",
        store=True,
        readonly=False,
        domain=[("type", "=", "sale")],
        help="Any self-billed invoices / credit notes received via Peppol will be created in draft in this journal. Defaults to the first sale journal.",
    )

    @api.constrains("account_peppol_phone_number")
    def _check_account_peppol_phone_number(self):
        for config in self:
            if config.account_peppol_phone_number:
                config.company_id._normalize_peppol_phone_number(
                    config.account_peppol_phone_number
                )

    @api.constrains("peppol_purchase_journal_id")
    def _check_peppol_purchase_journal_id(self):
        for company in self:
            if (
                company.peppol_purchase_journal_id
                and company.peppol_purchase_journal_id.type != "purchase"
            ):
                raise ValidationError(
                    self.env._(
                        "A purchase journal must be used to receive Peppol documents."
                    )
                )

    @api.depends("account_peppol_proxy_state")
    def _compute_peppol_purchase_journal_id(self):
        missing = self.filtered(
            lambda config: (
                not config.peppol_purchase_journal_id and config.peppol_can_send
            )
        )
        journal_by_company = missing.company_id._first_journal_per_company("purchase")
        for config in missing:
            config.peppol_purchase_journal_id = journal_by_company[config.company_id]
            config.peppol_purchase_journal_id.is_peppol_journal = True

    def _inverse_peppol_purchase_journal_id(self):
        # This avoid having 2 or more purchase journals from the same company with
        # `is_peppol_journal` set to True (which could occur after changes).
        journals_to_reset = self.env["account.journal"].search(
            [
                ("company_id", "in", self.company_id.ids),
                ("type", "=", "purchase"),
                ("is_peppol_journal", "=", True),
            ]
        )
        journals_to_reset.is_peppol_journal = False
        self.peppol_purchase_journal_id.is_peppol_journal = True

    @api.depends("account_peppol_proxy_state")
    def _compute_peppol_self_billing_reception_journal_id(self):
        missing = self.filtered(
            lambda config: (
                not config.peppol_self_billing_reception_journal_id
                and config.peppol_can_send
            )
        )
        journal_by_company = missing.company_id._first_journal_per_company("sale")
        for config in missing:
            config.peppol_self_billing_reception_journal_id = journal_by_company[
                config.company_id
            ]
            config.peppol_self_billing_reception_journal_id.is_peppol_journal = True

    def _inverse_peppol_self_billing_reception_journal_id(self):
        # This avoid having 2 or more sale journals from the same company with
        # `is_peppol_journal` set to True (which could occur after changes).
        journals_to_reset = self.env["account.journal"].search(
            [
                ("company_id", "in", self.company_id.ids),
                ("type", "=", "sale"),
                ("is_peppol_journal", "=", True),
            ]
        )
        journals_to_reset.is_peppol_journal = False
        self.peppol_self_billing_reception_journal_id.is_peppol_journal = True

    @api.depends("company_id.account_edi_proxy_client_ids")
    def _compute_account_peppol_edi_user(self):
        for config in self:
            config.account_peppol_edi_user = (
                config.company_id.account_edi_proxy_client_ids.filtered(
                    lambda u: u.proxy_type == "peppol"
                )
            )

    @api.depends("company_id.peppol_eas", "company_id.peppol_endpoint")
    def _compute_peppol_parent_company_id(self):
        self.peppol_parent_company_id = False
        for config in self:
            company = config.company_id
            for parent_company in company.parent_ids[::-1][1:]:
                if (
                    company.peppol_eas
                    and company.peppol_endpoint
                    and company.peppol_eas == parent_company.peppol_eas
                    and company.peppol_endpoint == parent_company.peppol_endpoint
                ) or (
                    not company.peppol_endpoint
                    and parent_company.peppol_eas
                    and parent_company.peppol_endpoint
                ):
                    config.peppol_parent_company_id = parent_company
                    break

    @api.depends("company_id.email")
    def _compute_account_peppol_contact_email(self):
        for config in self:
            if not config.account_peppol_contact_email:
                config.account_peppol_contact_email = config.company_id.email

    @api.depends("company_id.phone_ids")
    def _compute_account_peppol_phone_number(self):
        for config in self:
            if not config.account_peppol_phone_number:
                try:
                    # precompute only if it's a valid phone number
                    phone = config.company_id.phone_ids._primary().number
                    config.company_id._normalize_peppol_phone_number(phone)
                    config.account_peppol_phone_number = phone
                except ValidationError:
                    continue

    @api.depends("account_peppol_proxy_state")
    def _compute_peppol_can_send(self):
        can_send_domain = self.env[
            "account_edi_proxy_client.user"
        ]._get_domain_can_send()
        for config in self:
            config.peppol_can_send = (
                config.account_peppol_proxy_state in can_send_domain
            )

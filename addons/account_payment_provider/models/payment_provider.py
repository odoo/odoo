from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    journal_id = fields.Many2one(
        comodel_name="account.journal",
        string="Payment Journal",
        compute="_compute_journal_id",
        inverse="_inverse_journal_id",
        copy=False,
        domain='[("type", "=", "bank")]',
        check_company=True,
        help="The journal in which the successful transactions are posted.",
    )

    # === COMPUTE METHODS ===#

    def _sync_payment_channel(self, allow_create=True):
        self.check_singleton()
        if not self.id:
            return

        default_payment_method = self._get_provider_payment_method(self._get_code())
        if not default_payment_method:
            return

        pay_method_line = self.env["account.payment.channel"].search(
            [
                ("payment_provider_id", "=", self.id),
                ("journal_id", "!=", False),
            ],
            limit=1,
        )

        if not self.journal_id:
            if pay_method_line:
                pay_method_line.unlink()
                return

        if not pay_method_line:
            # Only reuse a line already sitting on the provider's own journal:
            # reusing one configured on a different journal would silently
            # move it away from wherever a user had it configured.
            pay_method_line = self.env["account.payment.channel"].search(
                [
                    *self.env["account.payment.channel"]._check_company_domain(
                        self.company_id
                    ),
                    ("code", "=", self._get_code()),
                    ("payment_provider_id", "=", False),
                    ("journal_id", "=", self.journal_id.id),
                ],
                limit=1,
            )
        if pay_method_line:
            pay_method_line.payment_provider_id = self
            pay_method_line.journal_id = self.journal_id
            pay_method_line.name = self.name
        elif allow_create:
            create_values = {
                "name": self.name,
                "payment_method_id": default_payment_method.id,
                "journal_id": self.journal_id.id,
                "payment_provider_id": self.id,
                "payment_account_id": self._get_payment_method_outstanding_account_id(
                    default_payment_method
                ),
            }
            pay_method_line_same_code = self.env["account.payment.channel"].search(
                [
                    *self.env["account.payment.channel"]._check_company_domain(
                        self.company_id
                    ),
                    ("code", "=", self._get_code()),
                ],
                limit=1,
            )
            if pay_method_line_same_code:
                create_values["payment_account_id"] = (
                    pay_method_line_same_code.payment_account_id.id
                )
            if self._get_code() == "sepa_direct_debit":
                create_values["name"] = "Online SEPA"
            self.env["account.payment.channel"].create(create_values)

    def _get_payment_method_outstanding_account_id(self, payment_method_id):
        if self.code == "custom":
            return False
        account_ref = (
            "account_journal_payment_debit_account_id"
            if payment_method_id.payment_type == "inbound"
            else "account_journal_payment_credit_account_id"
        )
        chart_template = self.with_context(
            allowed_company_ids=self.company_id.root_id.ids
        ).env["account.chart.template"]
        return (
            chart_template.ref(account_ref, raise_if_not_found=False)
            or self.company_id.account_config_id.transfer_account_id
        ).id

    @api.depends("code", "state", "company_id")
    def _compute_journal_id(self):
        first_channel_by_provider = {}
        for channel in self.env["account.payment.channel"].search(
            [
                ("payment_provider_id", "in", self._origin.ids),
                ("journal_id", "!=", False),
            ]
        ):
            first_channel_by_provider.setdefault(channel.payment_provider_id, channel)
        first_bank_journal_by_company = {}
        for journal in self.env["account.journal"].search(
            [("company_id", "in", self.company_id.ids), ("type", "=", "bank")]
        ):
            first_bank_journal_by_company.setdefault(journal.company_id, journal)

        for provider in self:
            pay_method_line = first_channel_by_provider.get(provider._origin)

            if pay_method_line:
                provider.journal_id = pay_method_line.journal_id
            elif provider.state in ("enabled", "test"):
                provider.journal_id = first_bank_journal_by_company.get(
                    provider.company_id, self.env["account.journal"]
                )
                if provider.id:
                    provider._sync_payment_channel()

    def _inverse_journal_id(self):
        for provider in self:
            provider._sync_payment_channel()

    @api.model
    def _get_provider_payment_method(self, code):
        return self.env["account.payment.method"].search([("code", "=", code)], limit=1)

    # === BUSINESS METHODS ===#

    @api.model
    def _setup_provider(self, code, **kwargs):
        """Override of `payment` to create the payment method of the provider."""
        super()._setup_provider(code, **kwargs)
        self._setup_payment_method(code)

    @api.model
    def _setup_payment_method(self, code):
        if code not in ("none", "custom") and not self._get_provider_payment_method(
            code
        ):
            providers_description = dict(
                self._fields["code"]._description_selection(self.env)
            )
            self.env["account.payment.method"].sudo().create(
                {
                    "name": providers_description[code],
                    "code": code,
                    "payment_type": "inbound",
                }
            )

    def _has_existing_payment(self, payment_method):
        existing_payment_count = self.env["account.payment"].search_count(
            [("payment_method_id", "=", payment_method.id)], limit=1
        )
        return bool(existing_payment_count)

    @api.model
    def _remove_provider(self, code, **kwargs):
        """Override of `payment` to delete the payment method of the provider."""
        payment_method = self._get_provider_payment_method(code)
        # If the payment method is used by any payments, we block the uninstallation of the module.
        if self._has_existing_payment(payment_method):
            raise UserError(
                _(
                    "You cannot uninstall this module as payments using this payment method already exist."
                )
            )
        super()._remove_provider(code, **kwargs)
        payment_method.unlink()

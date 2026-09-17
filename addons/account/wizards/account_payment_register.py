from collections import defaultdict
from datetime import date

import markupsafe

from odoo import Command, _, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import OrderedSet, frozendict
from odoo.tools.misc import clean_context

_debug = DebugLog(__name__)


class AccountPaymentRegister(models.TransientModel):
    _name = "account.payment.register"
    _inherit = ["mixin.payment.qr.code"]
    _description = "Pay"
    _check_company_auto = True

    payment_date = fields.Date(
        default=fields.Date.context_today,
        required=True,
    )
    amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_amount",
        store=True,
        readonly=False,
    )
    hide_writeoff_section = fields.Boolean(compute="_compute_hide_writeoff_section")
    communication = fields.Char(
        string="Memo",
        compute="_compute_communication",
        store=True,
        readonly=False,
    )
    group_payment = fields.Boolean(
        string="Group Payments",
        compute="_compute_group_payment",
        store=True,
        readonly=False,
        help="Only one payment will be created by partner (bank), instead of one per bill.",
    )
    early_payment_discount_mode = fields.Boolean(
        compute="_compute_early_payment_discount_mode"
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        precompute=True,
        store=True,
        readonly=False,
        help="The payment's currency.",
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        compute="_compute_journal_id",
        precompute=True,
        store=True,
        readonly=False,
        domain="[('id', 'in', available_journal_ids)]",
        check_company=True,
    )
    available_journal_ids = fields.Many2many(
        comodel_name="account.journal",
        compute="_compute_available_journal_ids",
    )
    available_partner_bank_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        compute="_compute_available_partner_bank_ids",
    )
    partner_bank_id = fields.Many2one(
        comodel_name="res.partner.bank",
        string="Recipient Bank Account",
        compute="_compute_partner_bank_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', available_partner_bank_ids)]",
    )
    company_currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
        string="Company Currency",
    )
    qr_code = fields.Html(
        string="QR Code URL",
        compute="_compute_qr_code",
    )

    batches = fields.Binary(
        export_string_translation=False,
        compute="_compute_batches",
    )
    total_amounts_to_pay = fields.Binary(
        export_string_translation=False,
        compute="_compute_total_amounts_to_pay",
    )
    installments_mode = fields.Selection(
        selection=[
            ("next", "Next Installment"),
            ("overdue", "Overdue Amount"),
            ("before_date", "Before Next Payment Date"),
            ("full", "Full Amount"),
        ],
        export_string_translation=False,
        compute="_compute_installments_mode",
        store=True,
        readonly=False,
    )
    installments_switch_html = fields.Html(
        compute="_compute_installments_switch_values"
    )
    installments_switch_amount = fields.Monetary(
        currency_field="currency_id",
        compute="_compute_installments_switch_values",
    )
    custom_user_amount = fields.Monetary(currency_field="currency_id")
    custom_user_currency_id = fields.Many2one(comodel_name="res.currency")

    line_ids = fields.Many2many(
        comodel_name="account.move.line",
        relation="account_payment_register_move_line_rel",
        column1="wizard_id",
        column2="line_id",
        string="Journal items",
        copy=False,
        readonly=True,
    )
    payment_type = fields.Selection(
        selection=[
            ("outbound", "Send Money"),
            ("inbound", "Receive Money"),
        ],
        compute="_compute_from_lines",
        store=True,
        copy=False,
    )
    partner_type = fields.Selection(
        selection=[
            ("customer", "Customer"),
            ("supplier", "Vendor"),
        ],
        compute="_compute_from_lines",
        store=True,
        copy=False,
    )
    source_amount = fields.Monetary(
        string="Amount to Pay (company currency)",
        currency_field="company_currency_id",
        compute="_compute_from_lines",
        store=True,
        copy=False,
    )
    source_amount_currency = fields.Monetary(
        string="Amount to Pay (foreign currency)",
        currency_field="source_currency_id",
        compute="_compute_from_lines",
        store=True,
        copy=False,
    )
    source_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_from_lines",
        store=True,
        copy=False,
    )
    can_edit_wizard = fields.Boolean(
        compute="_compute_from_lines",
        store=True,
        copy=False,
    )
    can_group_payments = fields.Boolean(
        compute="_compute_can_group_payments",
        store=True,
        copy=False,
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_from_lines",
        store=True,
        copy=False,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Customer/Vendor",
        compute="_compute_from_lines",
        store=True,
        copy=False,
        ondelete="restrict",
    )

    payment_channel_id = fields.Many2one(
        comodel_name="account.payment.channel",
        string="Payment Method",
        compute="_compute_payment_channel_id",
        store=True,
        readonly=False,
        domain="[('id', 'in', available_payment_channel_ids)]",
        help="Manual: Pay or Get paid by any method outside of Odoo.\n"
        "Payment Providers: Each payment provider has its own Payment Method. Request a transaction on/to a card thanks to a payment token saved by the partner when buying or subscribing online.\n"
        "Check: Pay bills by check and print it from Odoo.\n"
        "Batch Deposit: Collect several customer checks at once generating and submitting a batch deposit to your bank. Module account_batch_payment is necessary.\n"
        "SEPA Credit Transfer: Pay in the SEPA zone by submitting a SEPA Credit Transfer file to your bank. Module account_sepa is necessary.\n"
        "SEPA Direct Debit: Get paid in the SEPA zone thanks to a mandate your partner will have granted to you. Module account_sepa is necessary.\n",
    )
    available_payment_channel_ids = fields.Many2many(
        comodel_name="account.payment.channel",
        compute="_compute_available_payment_channel_ids",
    )
    payment_method_code = fields.Char(related="payment_channel_id.code")

    payment_difference = fields.Monetary(compute="_compute_payment_difference")
    payment_difference_handling = fields.Selection(
        selection=[("open", "Keep open"), ("reconcile", "Mark as fully paid")],
        compute="_compute_payment_difference_handling",
        store=True,
        readonly=False,
    )
    writeoff_account_id = fields.Many2one(
        comodel_name="account.account",
        string="Difference Account",
        copy=False,
        check_company=True,
    )
    writeoff_label = fields.Char(
        string="Journal Item Label",
        default="Write-Off",
        help="Change label of the counterpart that will hold the payment difference",
    )
    writeoff_is_exchange_account = fields.Boolean(
        compute="_compute_writeoff_is_exchange_account"
    )
    show_payment_difference = fields.Boolean(compute="_compute_show_payment_difference")

    show_partner_bank_account = fields.Boolean(
        compute="_compute_show_require_partner_bank"
    )
    require_partner_bank_account = fields.Boolean(
        compute="_compute_show_require_partner_bank"
    )
    country_code = fields.Char(
        related="company_id.account_fiscal_country_id.code",
        readonly=True,
    )
    duplicate_payment_ids = fields.Many2many(
        comodel_name="account.payment",
        compute="_compute_duplicate_payment_ids",
    )
    is_register_payment_on_draft = fields.Boolean(
        compute="_compute_is_register_payment_on_draft"
    )
    actionable_errors = fields.Json(compute="_compute_actionable_errors")

    untrusted_bank_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        compute="_compute_trust_values",
    )
    total_payments_amount = fields.Integer(compute="_compute_trust_values")
    untrusted_payments_count = fields.Integer(compute="_compute_trust_values")
    missing_account_partners = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_trust_values",
    )

    @api.model
    def _get_communication(self, lines):
        if len(lines.move_id) == 1:
            move = lines.move_id
            label = move.payment_reference or move.ref or move.name
        elif any(move.is_outbound() for move in lines.move_id):
            labels = {
                move.payment_reference or move.ref or move.name
                for move in lines.move_id
            }
            return ", ".join(sorted(filter(lambda l: l, labels)))
        else:
            label = self.company_id.get_next_batch_payment_communication()
        return label

    @api.model
    def _get_batch_available_journals(self, batch_result, company=None):
        payment_type = batch_result["payment_values"]["payment_type"]
        company = company or self._get_payment_company(batch_result["lines"])
        journals = self.env["account.journal"].search(
            [
                *self.env["account.journal"]._check_company_domain(company),
                ("type", "in", ("bank", "cash", "credit")),
            ]
        )
        if payment_type == "inbound":
            return journals.filtered("inbound_payment_channel_ids")
        else:
            return journals.filtered("outbound_payment_channel_ids")

    @api.model
    @_debug.perf.timed
    def _get_batch_journal(self, batch_result):
        payment_values = batch_result["payment_values"]
        foreign_currency_id = payment_values["currency_id"]
        partner_bank_id = payment_values["partner_bank_id"]
        company = self._get_payment_company(batch_result["lines"])

        currency_domain = [("currency_id", "=", foreign_currency_id)]
        partner_bank_domain = [("bank_account_id", "=", partner_bank_id)]

        default_domain = [
            *self.env["account.journal"]._check_company_domain(company),
            ("type", "in", ("bank", "cash", "credit")),
            ("id", "in", self.available_journal_ids.ids),
        ]

        if partner_bank_id:
            extra_domains = (
                currency_domain + partner_bank_domain,
                partner_bank_domain,
                currency_domain,
                [],
            )
        else:
            extra_domains = (
                currency_domain,
                [],
            )

        for extra_domain in extra_domains:
            journal = self._get_first_journal(default_domain + extra_domain)
            if journal:
                _debug.logic(
                    "batch_journal_chosen",
                    register=self,
                    journal=journal,
                    company=company,
                    with_partner_bank=bool(partner_bank_id),
                    extra_domain=extra_domain,
                )
                return journal

        _debug.logic(
            "batch_journal_not_found",
            register=self,
            company=company,
            with_partner_bank=bool(partner_bank_id),
            currency_id=foreign_currency_id,
        )
        return self.env["account.journal"]

    @api.model
    def _get_first_journal(self, domain):
        return self.env["account.journal"].search(domain, limit=1)

    @api.model
    def _get_batch_available_partner_banks(self, batch_result, journal):
        payment_values = batch_result["payment_values"]

        if payment_values["payment_type"] == "inbound":
            return journal.bank_account_id
        else:
            company = self._get_payment_company(batch_result["lines"])
            return (
                batch_result["lines"]
                .partner_id.bank_ids.filtered(
                    lambda x: x.company_id.id in (False, company.id)
                )
                ._origin
            )

    @api.model
    def _get_line_batch_key(self, line):
        move = line.move_id

        partner_bank_account = self.env["res.partner.bank"]
        if move.is_invoice(include_receipts=True):
            partner_bank_account = move.partner_bank_id._origin

        return {
            "partner_id": line.partner_id.id,
            "account_id": line.account_id.id,
            "currency_id": line.currency_id.id,
            "partner_bank_id": partner_bank_account.id,
            "partner_type": "customer"
            if line.account_type == "asset_receivable"
            else "supplier",
        }

    @api.model
    def _get_wizard_values_from_batch(self, batch_result):
        payment_values = batch_result["payment_values"]
        lines = batch_result["lines"]
        company = self._get_payment_company(lines)

        source_amount = abs(sum(lines.mapped("amount_residual")))
        if payment_values["currency_id"] == company.currency_id.id:
            source_amount_currency = source_amount
        else:
            source_amount_currency = abs(sum(lines.mapped("amount_residual_currency")))

        return {
            "company_id": company.id,
            "partner_id": payment_values["partner_id"],
            "partner_type": payment_values["partner_type"],
            "payment_type": payment_values["payment_type"],
            "source_currency_id": payment_values["currency_id"],
            "source_amount": source_amount,
            "source_amount_currency": source_amount_currency,
        }

    @api.model
    def _is_from_sibling_companies(self, lines):
        return len(lines.company_id) > 1 and not any(
            c.root_id in lines.company_id for c in lines.company_id
        )

    @api.model
    def _get_payment_company(self, lines):
        companies = lines.company_id
        if not companies:
            return self.env["res.company"]
        if self._is_from_sibling_companies(lines):
            return companies.root_id
        return min(companies, key=lambda c: len(c.sudo().parent_ids))

    @api.depends(
        "early_payment_discount_mode",
        "can_edit_wizard",
        "can_group_payments",
        "group_payment",
        "payment_channel_id",
    )
    def _compute_show_payment_difference(self):
        for wizard in self:
            wizard.show_payment_difference = (
                wizard.payment_difference != 0
                and not wizard.early_payment_discount_mode
                and wizard.can_edit_wizard
                and (not wizard.can_group_payments or wizard.group_payment)
                and wizard.payment_channel_id.payment_account_id
            )

    @api.depends("line_ids")
    @_debug.perf.timed
    def _compute_batches(self):
        for wizard in self:
            lines = wizard.line_ids._origin.sorted("id")

            if len(lines.company_id.root_id) > 1:
                raise UserError(
                    _(
                        "You can't create payments for entries belonging to different companies."
                    )
                )
            if not lines:
                raise UserError(
                    _(
                        "You can't open the register payment wizard without at least one receivable/payable line."
                    )
                )

            batches = defaultdict(lambda: {"lines": self.env["account.move.line"]})
            banks_per_partner = defaultdict(
                lambda: {"inbound": OrderedSet(), "outbound": OrderedSet()}
            )
            for line in lines:
                batch_key = self._get_line_batch_key(line)
                vals = batches[frozendict(batch_key)]
                vals["payment_values"] = batch_key
                vals["lines"] += line
                banks_per_partner[batch_key["partner_id"]][
                    "inbound" if line.balance > 0.0 else "outbound"
                ].add(batch_key["partner_bank_id"])

            partner_unique_inbound = {
                p for p, b in banks_per_partner.items() if len(b["inbound"]) == 1
            }
            partner_unique_outbound = {
                p for p, b in banks_per_partner.items() if len(b["outbound"]) == 1
            }

            batch_vals = []
            seen_keys = set()
            for i, key in enumerate(list(batches)):
                if key in seen_keys:
                    continue
                vals = batches[key]
                lines = vals["lines"]
                merge = (
                    key["partner_id"] in partner_unique_inbound
                    and key["partner_id"] in partner_unique_outbound
                )
                if merge:
                    for other_key in list(batches)[i + 1 :]:
                        if other_key in seen_keys:
                            continue
                        other_vals = batches[other_key]
                        if all(
                            other_vals["payment_values"][k] == v
                            for k, v in vals["payment_values"].items()
                            if k not in ("partner_bank_id", "payment_type")
                        ):
                            lines += other_vals["lines"]
                            seen_keys.add(other_key)
                balance = sum(lines.mapped("balance"))
                vals["payment_values"]["payment_type"] = (
                    "inbound" if balance > 0.0 else "outbound"
                )
                if merge:
                    partner_banks = banks_per_partner[key["partner_id"]]
                    vals["payment_values"]["partner_bank_id"] = next(
                        iter(partner_banks[vals["payment_values"]["payment_type"]])
                    )
                    vals["lines"] = lines
                batch_vals.append(vals)

            if _debug.logic.enabled:
                _debug.logic(
                    "_compute_batches",
                    line_count=len(lines),
                    batch_count=len(batch_vals),
                    batches=[
                        (b["payment_values"]["payment_type"], len(b["lines"]))
                        for b in batch_vals
                    ],
                )
            wizard.batches = batch_vals

    @api.depends("batches", "currency_id", "payment_date")
    def _compute_total_amounts_to_pay(self):
        for wizard in self:
            wizard.total_amounts_to_pay = wizard._get_total_amounts_to_pay(
                wizard.batches
            )

    @api.depends("payment_channel_id", "line_ids", "group_payment", "partner_bank_id")
    @_debug.perf.timed
    def _compute_trust_values(self):
        for wizard in self:
            untrusted_payments_count = 0
            untrusted_accounts = self.env["res.partner.bank"]
            missing_account_partners = self.env["res.partner"]

            total_payment_count = len(wizard.batches)
            if not wizard.group_payment:
                total_amount_values = wizard.total_amounts_to_pay
                total_payment_count = len(total_amount_values["lines"])

            for batch in wizard.batches:
                batch_account = wizard.partner_bank_id or wizard._get_batch_account(
                    batch
                )
                if wizard.require_partner_bank_account:
                    if not batch_account:
                        missing_account_partners += batch["lines"].partner_id
                    elif not batch_account.allow_out_payment:
                        untrusted_payments_count += (
                            1
                            if wizard.group_payment
                            else len(
                                batch["lines"].filtered(
                                    lambda line, total_amount_values=total_amount_values: (
                                        line in total_amount_values["lines"]
                                    )
                                )
                            )
                        )
                        untrusted_accounts |= batch_account

            _debug.logic(
                "trust_values_computed",
                register=wizard,
                payments=total_payment_count,
                untrusted_payments=untrusted_payments_count,
                untrusted_accounts=untrusted_accounts,
                missing_account_partners=missing_account_partners,
            )
            wizard.update(
                {
                    "total_payments_amount": total_payment_count,
                    "untrusted_payments_count": untrusted_payments_count,
                    "untrusted_bank_ids": untrusted_accounts or False,
                    "missing_account_partners": missing_account_partners or False,
                }
            )

    @api.depends("line_ids")
    @_debug.perf.timed
    def _compute_from_lines(self):
        for wizard in self:
            batch_result = wizard.batches[0]
            wizard_values_from_batch = wizard._get_wizard_values_from_batch(
                batch_result
            )

            if len(wizard.batches) == 1:
                wizard.update(wizard_values_from_batch)

                wizard.can_edit_wizard = True
            else:
                lines = sum(
                    (batch_result["lines"] for batch_result in wizard.batches),
                    self.env["account.move.line"],
                )
                company = wizard._get_payment_company(lines)
                wizard.update(
                    {
                        "company_id": company.id,
                        "partner_id": False,
                        "partner_type": False,
                        "payment_type": wizard_values_from_batch["payment_type"],
                        "source_currency_id": False,
                        "source_amount": False,
                        "source_amount_currency": False,
                    }
                )

                wizard.can_edit_wizard = False

    @api.depends("batches", "amount")
    @_debug.perf.timed
    def _compute_can_group_payments(self):
        for wizard in self:
            if len(wizard.batches) == 1:
                lines = wizard.batches[0]["lines"]
                wizard.can_group_payments = len(lines) != 1 and not (
                    len(lines.move_id) == 1
                    and lines.move_id.is_invoice(include_receipts=True)
                )
            else:
                total_amounts_to_pay = wizard.total_amounts_to_pay
                wizard.can_group_payments = any(
                    len(
                        batch_result["lines"].filtered(
                            lambda line, total_amounts_to_pay=total_amounts_to_pay: (
                                line in total_amounts_to_pay["lines"]
                            )
                        )
                    )
                    != 1
                    for batch_result in wizard.batches
                )

    @api.depends("can_edit_wizard", "amount")
    def _compute_communication(self):
        for wizard in self:
            if (
                wizard.can_edit_wizard and wizard.installments_mode == "full"
            ) or wizard.custom_user_amount:
                lines = wizard.line_ids
            else:
                lines = wizard.total_amounts_to_pay["lines"]
            wizard.communication = wizard._get_communication(lines)

    @api.depends("can_edit_wizard")
    def _compute_group_payment(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.group_payment = len(wizard.batches[0]["lines"].move_id) == 1
            else:
                wizard.group_payment = False

    @api.depends("journal_id")
    def _compute_currency_id(self):
        for wizard in self:
            wizard.currency_id = (
                wizard.journal_id.currency_id
                or wizard.source_currency_id
                or wizard.company_id.currency_id
            )

    @api.depends("payment_type", "company_id", "can_edit_wizard")
    def _compute_available_journal_ids(self):
        for wizard in self:
            available_journals = self.env["account.journal"]
            for batch in wizard.batches:
                available_journals |= wizard._get_batch_available_journals(
                    batch, company=wizard.company_id
                )
            wizard.available_journal_ids = [Command.set(available_journals.ids)]

    @api.depends("available_journal_ids")
    @_debug.perf.timed
    def _compute_journal_id(self):
        Journal = self.env["account.journal"]
        fallback_journals = Journal.search(
            [
                *Journal._check_company_domain(self.company_id),
                ("type", "in", ("bank", "cash", "credit")),
                ("id", "in", self.available_journal_ids.ids),
            ]
        )
        for wizard in self:
            if wizard.journal_id in wizard.available_journal_ids:
                continue
            move_payment_channels = wizard.line_ids.move_id.preferred_payment_channel_id
            if move_payment_channels and len(move_payment_channels) == 1:
                _debug.logic(
                    "register_journal_chosen", register=wizard, source="move_channel"
                )
                wizard.journal_id = move_payment_channels.journal_id
            elif wizard.can_edit_wizard:
                _debug.logic("register_journal_chosen", register=wizard, source="batch")
                batch = wizard.batches[0]
                wizard.journal_id = wizard._get_batch_journal(batch)
            else:
                _debug.logic(
                    "register_journal_chosen",
                    register=wizard,
                    source="fallback",
                    fallback_journals=fallback_journals,
                )
                wizard.journal_id = fallback_journals.filtered_domain(
                    Journal._check_company_domain(wizard.company_id)
                )[:1]

    @api.depends("can_edit_wizard", "journal_id")
    def _compute_available_partner_bank_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard.batches[0]
                wizard.available_partner_bank_ids = (
                    wizard._get_batch_available_partner_banks(batch, wizard.journal_id)
                )
            else:
                wizard.available_partner_bank_ids = None

    @api.depends("journal_id", "available_partner_bank_ids")
    def _compute_partner_bank_id(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                batch = wizard.batches[0]
                partner_bank_id = batch["payment_values"]["partner_bank_id"]
                available_partner_banks = wizard.available_partner_bank_ids._origin
                if partner_bank_id and partner_bank_id in available_partner_banks.ids:
                    wizard.partner_bank_id = self.env["res.partner.bank"].browse(
                        partner_bank_id
                    )
                else:
                    wizard.partner_bank_id = available_partner_banks[:1]
            else:
                wizard.partner_bank_id = None

    @api.depends("payment_type", "journal_id", "currency_id")
    def _compute_available_payment_channel_ids(self):
        for wizard in self:
            if wizard.journal_id:
                wizard.available_payment_channel_ids = (
                    wizard.journal_id._get_available_payment_channels(
                        wizard.payment_type
                    )
                )
            else:
                wizard.available_payment_channel_ids = False

    @api.depends("payment_type", "journal_id")
    @_debug.perf.timed
    def _compute_payment_channel_id(self):
        for wizard in self:
            if wizard.journal_id:
                available_payment_channels = (
                    wizard.journal_id._get_available_payment_channels(
                        wizard.payment_type
                    )
                )
            else:
                available_payment_channels = False

            if (
                available_payment_channels
                and wizard.payment_channel_id in available_payment_channels
            ):
                continue

            if available_payment_channels:
                move_payment_channels = (
                    wizard.line_ids.move_id.preferred_payment_channel_id
                )
                if (
                    len(move_payment_channels) == 1
                    and move_payment_channels.id in available_payment_channels.ids
                ):
                    _debug.logic(
                        "register_channel_chosen",
                        register=wizard,
                        source="move_channel",
                    )
                    wizard.payment_channel_id = move_payment_channels
                else:
                    _debug.logic(
                        "register_channel_chosen",
                        register=wizard,
                        source="first_available",
                    )
                    wizard.payment_channel_id = available_payment_channels[0]._origin
            else:
                _debug.logic(
                    "register_channel_chosen", register=wizard, source="none_available"
                )
                wizard.payment_channel_id = False

    @api.depends("payment_channel_id")
    def _compute_show_require_partner_bank(self):
        for wizard in self:
            if wizard.journal_id.type == "cash":
                wizard.show_partner_bank_account = False
            else:
                wizard.show_partner_bank_account = (
                    wizard.payment_channel_id.code
                    in self.env[
                        "account.payment"
                    ]._get_method_codes_using_bank_account()
                )
            wizard.require_partner_bank_account = (
                wizard.payment_channel_id.code
                in self.env["account.payment"]._get_method_codes_needing_bank_account()
            )

    @api.depends("line_ids")
    @_debug.perf.timed
    def _compute_actionable_errors(self):
        for wizard in self:
            actionable_errors = {}
            if (
                unpaid_matched_payments
                := wizard.line_ids.move_id.reconciled_payment_ids.filtered(
                    lambda p: p.state == "in_process"
                )
            ):
                actionable_errors["unpaid_matched_payments"] = {
                    "message": self.env._(
                        "There are payments in progress. Make sure you don't pay twice."
                    ),
                    "action_text": self.env._("Check them"),
                    "action": unpaid_matched_payments._get_records_action(
                        name=self.env._("Payments")
                    ),
                    "level": "danger",
                }
            wizard.actionable_errors = actionable_errors

    @_debug.perf.timed
    def _convert_to_wizard_currency(self, installments):
        self.check_singleton()
        total_per_currency = defaultdict(
            lambda: {
                "amount_residual": 0.0,
                "amount_residual_currency": 0.0,
            }
        )
        for installment in installments:
            line = installment["line"]
            total_per_currency[line.currency_id]["amount_residual"] += installment[
                "amount_residual"
            ]
            total_per_currency[line.currency_id]["amount_residual_currency"] += (
                installment["amount_residual_currency"]
            )

        total_amount = 0.0
        wizard_curr = self.currency_id
        comp_curr = self.company_currency_id
        for currency, amounts in total_per_currency.items():
            amount_residual = amounts["amount_residual"]
            amount_residual_currency = amounts["amount_residual_currency"]
            if currency == wizard_curr:
                total_amount += amount_residual_currency
            elif currency != comp_curr and wizard_curr == comp_curr:
                total_amount += currency._convert(
                    amount_residual_currency,
                    comp_curr,
                    self.company_id,
                    self.payment_date,
                )
            else:
                total_amount += comp_curr._convert(
                    amount_residual, wizard_curr, self.company_id, self.payment_date
                )
        _debug.pipeline(
            "installments_converted",
            register=self,
            installments=len(installments),
            currencies=len(total_per_currency),
            wizard_currency=wizard_curr,
            total_amount=total_amount,
        )
        return total_amount

    @_debug.perf.timed
    def _get_total_amounts_to_pay(self, batch_results):
        self.check_singleton()
        next_payment_date = self._extract_next_payment_date_from_context()
        amount_per_line_common = []
        amount_per_line_by_default = []
        amount_per_line_full_amount = []
        amount_per_line_for_difference = []
        epd_applied = False
        first_installment_mode = False
        all_lines = self.env["account.move.line"]
        for batch_result in batch_results:
            all_lines |= batch_result["lines"]
        all_lines = all_lines.sorted(
            key=lambda line: (line.move_id.id, line.date_maturity or date.max)
        )
        for lines in all_lines.grouped("move_id").values():
            installments = lines._prepare_installments_data(
                payment_currency=self.currency_id,
                payment_date=self.payment_date,
                next_payment_date=next_payment_date,
            )
            last_installment_mode = False
            for installment in installments:
                line = installment["line"]
                if installment["type"] == "early_payment_discount":
                    epd_applied = True
                    amount_per_line_by_default.append(installment)
                    amount_per_line_for_difference.append(
                        {
                            **installment,
                            "amount_residual_currency": line.amount_residual_currency,
                            "amount_residual": line.amount_residual,
                        }
                    )
                    continue

                if line.display_type == "payment_term" and installment["type"] in (
                    "overdue",
                    "next",
                    "before_date",
                ):
                    if installment["type"] == "overdue":
                        amount_per_line_common.append(installment)
                    elif installment["type"] == "before_date":
                        amount_per_line_common.append(installment)
                        first_installment_mode = "before_date"
                    elif installment["type"] == "next":
                        if last_installment_mode in ("next", "overdue", "before_date"):
                            amount_per_line_full_amount.append(installment)
                        elif not last_installment_mode:
                            amount_per_line_common.append(installment)
                            first_installment_mode = "next"
                    last_installment_mode = installment["type"]
                    first_installment_mode = (
                        first_installment_mode or last_installment_mode
                    )
                    continue

                amount_per_line_common.append(installment)

        common = self._convert_to_wizard_currency(amount_per_line_common)
        by_default = self._convert_to_wizard_currency(amount_per_line_by_default)
        for_difference = self._convert_to_wizard_currency(
            amount_per_line_for_difference
        )
        full_amount = self._convert_to_wizard_currency(amount_per_line_full_amount)

        lines = self.env["account.move.line"]
        for value in amount_per_line_common + amount_per_line_by_default:
            lines |= value["line"]
        _debug.logic(
            "amounts",
            register=self,
            common=common,
            by_default=by_default,
            full=full_amount,
            for_difference=for_difference,
            epd=epd_applied,
            first_mode=first_installment_mode,
            lines=len(lines),
        )

        return {
            "amount_by_default": abs(common + by_default),
            "full_amount": abs(common + by_default + full_amount),
            "amount_for_difference": abs(common + for_difference),
            "full_amount_for_difference": abs(common + for_difference + full_amount),
            "epd_applied": epd_applied,
            "installment_mode": first_installment_mode,
            "lines": lines,
        }

    @api.onchange("amount")
    def _onchange_amount(self):
        if not self.can_edit_wizard or not self.currency_id:
            _debug.logic(
                "amount_onchange_skipped",
                register=self,
                reason="not_editable_or_no_currency",
            )
            return

        total_amount_values = self.total_amounts_to_pay
        is_custom_user_amount = all(
            not self.currency_id.is_zero(
                self.amount - total_amount_values[amount_field]
            )
            for amount_field in (
                "amount_by_default",
                "amount_for_difference",
                "full_amount",
                "full_amount_for_difference",
            )
        )
        _debug.logic(
            "custom_user_amount_decided",
            register=self,
            custom=is_custom_user_amount,
        )
        if is_custom_user_amount:
            self.custom_user_amount = self.amount
            self.custom_user_currency_id = self.currency_id
        else:
            self.custom_user_amount = None
            self.custom_user_currency_id = None

    @api.onchange("currency_id")
    def _onchange_currency_id(self):
        if (
            not self.can_edit_wizard
            or not self.currency_id
            or not self.payment_date
            or not self.custom_user_amount
        ):
            _debug.logic("currency_onchange_skipped", register=self)
            return

        if self.custom_user_amount:
            _debug.logic(
                "custom_user_amount_converted",
                register=self,
                from_currency=self.custom_user_currency_id,
                to_currency=self.currency_id,
            )
            self.custom_user_amount = self.amount = (
                self.custom_user_currency_id._convert(
                    from_amount=self.custom_user_amount,
                    to_currency=self.currency_id,
                    date=self.payment_date,
                    company=self.company_id,
                )
            )

    @api.onchange("payment_date")
    def _onchange_payment_date(self):
        if (
            not self.can_edit_wizard
            or not self.currency_id
            or not self.payment_date
            or not self.custom_user_amount
        ):
            return

        self.amount = self.custom_user_amount

    @api.depends(
        "can_edit_wizard",
        "source_amount",
        "source_amount_currency",
        "source_currency_id",
        "company_id",
        "currency_id",
        "payment_date",
        "installments_mode",
    )
    def _compute_amount(self):
        for wizard in self:
            if (
                not wizard.journal_id
                or not wizard.currency_id
                or not wizard.payment_date
                or wizard.custom_user_amount
            ):
                wizard.amount = wizard.amount
            else:
                total_amount_values = wizard.total_amounts_to_pay
                wizard.amount = total_amount_values["amount_by_default"]

    @api.depends("amount")
    @_debug.perf.timed
    def _compute_installments_mode(self):
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id:
                wizard.installments_mode = wizard.installments_mode
            else:
                total_amount_values = wizard.total_amounts_to_pay
                if (
                    wizard.currency_id.compare_amounts(
                        wizard.amount, total_amount_values["full_amount"]
                    )
                    == 0
                ):
                    wizard.installments_mode = "full"
                elif (
                    wizard.currency_id.compare_amounts(
                        wizard.amount, total_amount_values["amount_by_default"]
                    )
                    == 0
                ):
                    wizard.installments_mode = total_amount_values["installment_mode"]
                else:
                    wizard.installments_mode = "full"
        if _debug.logic.enabled:
            _debug.logic(
                "installments_mode_decided",
                register=self,
                modes=self.mapped("installments_mode"),
            )

    @api.depends("installments_mode")
    @_debug.perf.timed
    def _compute_installments_switch_values(self):
        for wizard in self:
            if not wizard.journal_id or not wizard.currency_id:
                _debug.logic(
                    "installments_switch_skipped",
                    register=wizard,
                    reason="no_journal_or_currency",
                )
                wizard.installments_switch_amount = wizard.installments_switch_amount
                wizard.installments_switch_html = wizard.installments_switch_html
            else:
                total_amount_values = wizard.total_amounts_to_pay
                html_lines = []
                if wizard.installments_mode == "full":
                    is_full_match = wizard.currency_id.is_zero(
                        total_amount_values["full_amount"] - wizard.amount
                    ) and wizard.currency_id.is_zero(
                        total_amount_values["full_amount"]
                        - total_amount_values["amount_by_default"]
                    )
                    wizard.installments_switch_amount = (
                        0.0
                        if is_full_match
                        else total_amount_values["amount_by_default"]
                    )
                    if not is_full_match and not wizard.currency_id.is_zero(
                        wizard.amount
                    ):
                        switch_message = (
                            _(
                                "Consider paying the amount with %(btn_start)searly payment discount%(btn_end)s instead."
                            )
                            if total_amount_values["epd_applied"]
                            else _(
                                "Consider paying in %(btn_start)sinstallments%(btn_end)s instead."
                            )
                        )
                        html_lines += [
                            _("This is the full amount."),
                            switch_message,
                        ]
                elif wizard.installments_mode == "overdue":
                    wizard.installments_switch_amount = total_amount_values[
                        "full_amount"
                    ]
                    html_lines += [
                        _("This is the overdue amount."),
                        _("Consider paying the %(btn_start)sfull amount%(btn_end)s."),
                    ]
                elif wizard.installments_mode == "before_date":
                    wizard.installments_switch_amount = total_amount_values[
                        "full_amount"
                    ]
                    next_payment_date = self._extract_next_payment_date_from_context()
                    html_lines += [
                        _(
                            "Total for the installments before %(date)s.",
                            date=(next_payment_date or fields.Date.context_today(self)),
                        ),
                        _("Consider paying the %(btn_start)sfull amount%(btn_end)s."),
                    ]
                elif wizard.installments_mode == "next":
                    wizard.installments_switch_amount = total_amount_values[
                        "full_amount"
                    ]
                    html_lines += [
                        _("This is the next unreconciled installment."),
                        _("Consider paying the %(btn_start)sfull amount%(btn_end)s."),
                    ]
                else:
                    wizard.installments_switch_amount = (
                        wizard.installments_switch_amount
                    )

                if wizard.custom_user_amount:
                    wizard.installments_switch_html = None
                else:
                    wizard.installments_switch_html = markupsafe.Markup("<br/>").join(
                        html_lines
                    ) % {
                        "btn_start": markupsafe.Markup(
                            '<span class="installments_switch_button btn btn-link p-0 align-baseline">'
                        ),
                        "btn_end": markupsafe.Markup("</span>"),
                    }
                _debug.logic(
                    "installments_switch_decided",
                    register=wizard,
                    mode=wizard.installments_mode,
                    switch_amount=wizard.installments_switch_amount,
                    epd_applied=total_amount_values["epd_applied"],
                    custom_user_amount=wizard.custom_user_amount,
                    hint_lines=len(html_lines),
                )

    @api.depends("can_edit_wizard", "payment_date", "currency_id", "amount")
    @_debug.perf.timed
    def _compute_early_payment_discount_mode(self):
        for wizard in self:
            if (
                not wizard.journal_id
                or not wizard.currency_id
                or not wizard.payment_date
            ):
                wizard.early_payment_discount_mode = wizard.early_payment_discount_mode
            else:
                total_amount_values = wizard.total_amounts_to_pay
                wizard.early_payment_discount_mode = total_amount_values[
                    "epd_applied"
                ] and (
                    wizard.currency_id.compare_amounts(
                        wizard.amount, total_amount_values["amount_by_default"]
                    )
                    == 0
                    or wizard.currency_id.compare_amounts(
                        wizard.amount, total_amount_values["full_amount"]
                    )
                    == 0
                )

    @api.depends("can_edit_wizard", "amount", "installments_mode")
    @_debug.perf.timed
    def _compute_payment_difference(self):
        for wizard in self:
            if wizard.payment_date:
                total_amount_values = wizard.total_amounts_to_pay
                if wizard.installments_mode in ("overdue", "next", "before_date"):
                    wizard.payment_difference = (
                        total_amount_values["amount_for_difference"] - wizard.amount
                    )
                elif wizard.installments_mode == "full":
                    wizard.payment_difference = (
                        total_amount_values["full_amount_for_difference"]
                        - wizard.amount
                    )
                else:
                    wizard.payment_difference = (
                        total_amount_values["amount_for_difference"] - wizard.amount
                    )
            else:
                wizard.payment_difference = 0.0
            _debug.logic(
                "_compute_payment_difference",
                register=wizard,
                difference=wizard.payment_difference,
                amount=wizard.amount,
                mode=wizard.installments_mode,
                handling=wizard.payment_difference_handling,
            )

    @api.depends(
        "can_edit_wizard",
        "writeoff_account_id",
        "payment_difference_handling",
        "currency_id",
    )
    def _compute_writeoff_is_exchange_account(self):
        for wizard in self:
            wizard.writeoff_is_exchange_account = all(
                (
                    wizard.can_edit_wizard,
                    wizard.payment_difference_handling == "reconcile",
                    wizard.currency_id != wizard.source_currency_id,
                    wizard.writeoff_account_id,
                    wizard.writeoff_account_id
                    in (
                        wizard.company_id.expense_currency_exchange_account_id,
                        wizard.company_id.income_currency_exchange_account_id,
                    ),
                )
            )

    @api.depends("early_payment_discount_mode")
    def _compute_payment_difference_handling(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.payment_difference_handling = (
                    "reconcile" if wizard.early_payment_discount_mode else "open"
                )
            else:
                wizard.payment_difference_handling = False

    @api.depends("early_payment_discount_mode")
    def _compute_hide_writeoff_section(self):
        for wizard in self:
            wizard.hide_writeoff_section = wizard.early_payment_discount_mode

    @api.depends(
        "partner_bank_id",
        "amount",
        "currency_id",
        "payment_channel_id",
        "payment_type",
        "communication",
    )
    def _compute_qr_code(self):
        for pay in self:
            pay.qr_code = pay._render_payment_qr_code(pay.amount, pay.communication)

    @api.depends("partner_id", "amount", "payment_date", "payment_type", "line_ids")
    def _compute_duplicate_payment_ids(self):
        for wizard in self:
            if wizard.can_edit_wizard:
                wizard.duplicate_payment_ids = self._get_duplicate_reference().get(
                    0, self.env["account.payment"]
                )
            else:
                wizard.duplicate_payment_ids = self.env["account.payment"]

    @api.depends("line_ids")
    def _compute_is_register_payment_on_draft(self):
        for wizard in self:
            wizard.is_register_payment_on_draft = any(
                l.parent_state == "draft" for l in wizard.line_ids
            )

    def _get_duplicate_reference(self, matching_states=("draft", "posted")):
        dummy = self.env["account.payment"].new(
            {
                "company_id": self.company_id,
                "partner_id": self.partner_id,
                "date": self.payment_date,
                "amount": self.amount,
                "payment_type": self.payment_type,
            }
        )
        return dummy._get_duplicate_reference(matching_states)

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        _debug.lifecycle("default_get", records=self)
        res = super().default_get(fields)

        if "line_ids" in fields and "line_ids" not in res:
            if self.env.context.get("active_model") == "account.move":
                lines = (
                    self.env["account.move"]
                    .browse(self.env.context.get("active_ids", []))
                    .line_ids
                )
            elif self.env.context.get("active_model") == "account.move.line":
                lines = self.env["account.move.line"].browse(
                    self.env.context.get("active_ids", [])
                )
            else:
                raise UserError(
                    _(
                        "The register payment wizard should only be called on account.move or account.move.line records."
                    )
                )

            if "journal_id" in res and not self.env["account.journal"].browse(
                res["journal_id"]
            ).filtered_domain(
                [
                    *self.env["account.journal"]._check_company_domain(
                        lines.company_id
                    ),
                    ("type", "in", ("bank", "cash", "credit")),
                ]
            ):
                del res["journal_id"]

            available_lines = self.env["account.move.line"]
            valid_account_types = self.env[
                "account.payment"
            ]._get_valid_payment_account_types()
            for line in lines:
                if line.account_type not in valid_account_types:
                    continue
                if line.currency_id:
                    if line.currency_id.is_zero(line.amount_residual_currency):
                        continue
                elif line.company_currency_id.is_zero(line.amount_residual):
                    continue
                available_lines |= line

            _debug.pipeline(
                "payable_lines_filtered",
                active_model=self.env.context.get("active_model"),
                lines=lines,
                available=len(available_lines),
                journal_kept="journal_id" in res,
            )
            if not available_lines:
                raise UserError(
                    _(
                        "There's nothing left to pay for the selected journal items, so no payment registration is necessary. You've got your finances under control like a boss!"
                    )
                )
            if len(lines.company_id.root_id) > 1:
                raise UserError(
                    _(
                        "You can't create payments for entries belonging to different companies."
                    )
                )
            if (
                self._is_from_sibling_companies(lines)
                and lines.company_id.root_id not in self.env.user.company_ids
            ):
                raise UserError(
                    _(
                        "You can't create payments for entries belonging to different branches without access to parent company."
                    )
                )
            if len(set(available_lines.mapped("account_type"))) > 1:
                raise UserError(
                    _(
                        "You can't register payments for both inbound and outbound moves at the same time."
                    )
                )

            res["line_ids"] = [(6, 0, available_lines.ids)]

        return res

    def _prepare_early_payment_write_off_vals(
        self, lines, currency, open_amount_currency
    ):
        epd_aml_values_list = [
            {
                "aml": aml,
                "amount_currency": -aml.amount_residual_currency,
                "balance": aml.currency_id._convert(
                    -aml.amount_residual_currency,
                    self.company_id.currency_id,
                    self.company_id,
                    self.payment_date,
                ),
            }
            for aml in lines
            if aml.move_id._is_eligible_for_early_payment_discount(
                currency, self.payment_date
            )
        ]
        open_balance = currency._convert(
            open_amount_currency,
            self.company_id.currency_id,
            self.company_id,
            self.payment_date,
        )
        counterpart_vals = self.env[
            "account.move"
        ]._get_invoice_counterpart_amls_for_early_payment_discount(
            epd_aml_values_list, open_balance
        )
        return [vals for vals_list in counterpart_vals.values() for vals in vals_list]

    @_debug.perf.timed
    def _create_payment_vals_from_wizard(self, batch_result):
        payment_vals = {
            "date": self.payment_date,
            "amount": self.amount,
            "payment_type": self.payment_type,
            "partner_type": self.partner_type,
            "memo": self.communication,
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "currency_id": self.currency_id.id,
            "partner_id": self.partner_id.id,
            "partner_bank_id": self.partner_bank_id.id,
            "payment_channel_id": self.payment_channel_id.id,
            "destination_account_id": self.line_ids[0].account_id.id,
            "write_off_line_vals": [],
        }

        if self.payment_difference_handling == "reconcile":
            if self.early_payment_discount_mode:
                payment_vals["write_off_line_vals"] += (
                    self._prepare_early_payment_write_off_vals(
                        batch_result["lines"],
                        self.currency_id,
                        self.payment_difference
                        * (-1 if self.payment_type == "outbound" else 1),
                    )
                )
            elif not self.currency_id.is_zero(self.payment_difference):
                if self.writeoff_is_exchange_account:
                    if self.currency_id != self.company_currency_id:
                        payment_vals["force_balance"] = sum(
                            batch_result["lines"].mapped("amount_residual")
                        )
                else:
                    if self.payment_type == "inbound":
                        write_off_amount_currency = self.payment_difference
                    else:
                        write_off_amount_currency = -self.payment_difference

                    payment_vals["write_off_line_vals"].append(
                        {
                            "name": self.writeoff_label,
                            "account_id": self.writeoff_account_id.id,
                            "partner_id": self.partner_id.id,
                            "currency_id": self.currency_id.id,
                            "amount_currency": write_off_amount_currency,
                            "balance": self.currency_id._convert(
                                write_off_amount_currency,
                                self.company_id.currency_id,
                                self.company_id,
                                self.payment_date,
                            ),
                        }
                    )

        if _debug.logic.enabled:
            _debug.logic(
                "payment_difference_handled",
                register=self,
                handling=self.payment_difference_handling,
                epd_mode=self.early_payment_discount_mode,
                difference=self.payment_difference,
                exchange_account=self.writeoff_is_exchange_account,
                write_offs=len(payment_vals["write_off_line_vals"]),
                forced_balance="force_balance" in payment_vals,
            )
        return payment_vals

    @_debug.perf.timed
    def _create_payment_vals_from_batch(self, batch_result):
        batch_values = self._get_wizard_values_from_batch(batch_result)

        if batch_values["payment_type"] == "inbound":
            partner_bank_id = self.journal_id.bank_account_id.id
        else:
            partner_bank_id = batch_result["payment_values"]["partner_bank_id"]

        payment_channel = self.payment_channel_id

        if batch_values["payment_type"] != payment_channel.payment_type:
            payment_channel = self.journal_id._get_available_payment_channels(
                batch_values["payment_type"]
            )[:1]

        payment_vals = {
            "date": self.payment_date,
            "amount": batch_values["source_amount_currency"],
            "payment_type": batch_values["payment_type"],
            "partner_type": batch_values["partner_type"],
            "memo": self._get_communication(batch_result["lines"]),
            "journal_id": self.journal_id.id,
            "company_id": self.company_id.id,
            "currency_id": batch_values["source_currency_id"],
            "partner_id": batch_values["partner_id"],
            "payment_channel_id": payment_channel.id,
            "destination_account_id": batch_result["lines"][0].account_id.id,
            "write_off_line_vals": [],
        }

        if partner_bank_id:
            payment_vals["partner_bank_id"] = partner_bank_id

        total_amount_values = self._get_total_amounts_to_pay([batch_result])
        total_amount = total_amount_values["amount_by_default"]
        currency = self.env["res.currency"].browse(batch_values["source_currency_id"])
        if total_amount_values["epd_applied"]:
            payment_vals["amount"] = total_amount

            payment_vals["write_off_line_vals"] += (
                self._prepare_early_payment_write_off_vals(
                    batch_result["lines"],
                    currency,
                    (batch_values["source_amount_currency"] - total_amount)
                    * (-1 if batch_values["payment_type"] == "outbound" else 1),
                )
            )

        if _debug.logic.enabled:
            _debug.logic(
                "batch_payment_vals_built",
                register=self,
                payment_type=batch_values["payment_type"],
                channel_rerouted=payment_channel != self.payment_channel_id,
                partner_bank_id=partner_bank_id,
                epd_applied=total_amount_values["epd_applied"],
                amount=payment_vals["amount"],
                write_offs=len(payment_vals["write_off_line_vals"]),
            )
        return payment_vals

    @_debug.perf.timed
    def _init_payments(self, to_process, edit_mode=False):
        payments = (
            self.env["account.payment"]
            .with_context(skip_invoice_sync=True)
            .create([x["create_vals"] for x in to_process])
        )
        _debug.pipeline(
            "_init_payments", register=self, payments=payments, edit_mode=edit_mode
        )

        for payment, vals in zip(payments, to_process, strict=False):
            vals["payment"] = payment

            if edit_mode and payment.move_id:
                lines = vals["to_reconcile"]

                if payment.currency_id != lines.currency_id:
                    liquidity_lines, counterpart_lines, _writeoff_lines = (
                        payment._seek_for_lines()
                    )
                    source_balance = abs(sum(lines.mapped("amount_residual")))
                    if liquidity_lines[0].balance:
                        payment_rate = (
                            liquidity_lines[0].amount_currency
                            / liquidity_lines[0].balance
                        )
                    else:
                        payment_rate = 0.0
                    source_balance_converted = abs(source_balance) * payment_rate

                    payment_balance = abs(sum(counterpart_lines.mapped("balance")))
                    payment_amount_currency = abs(
                        sum(counterpart_lines.mapped("amount_currency"))
                    )
                    if not payment.currency_id.is_zero(
                        source_balance_converted - payment_amount_currency
                    ):
                        _debug.logic(
                            "edit_mode_amount_differs_source_no", payment=payment
                        )
                        continue

                    delta_balance = source_balance - payment_balance

                    if self.company_currency_id.is_zero(delta_balance):
                        continue
                    _debug.logic(
                        "edit_mode_rebalancing_entry",
                        payment=payment,
                        delta_balance=delta_balance,
                    )

                    debit_lines = (liquidity_lines + counterpart_lines).filtered(
                        "debit"
                    )
                    credit_lines = (liquidity_lines + counterpart_lines).filtered(
                        "credit"
                    )

                    if debit_lines and credit_lines:
                        payment.move_id.write(
                            {
                                "line_ids": [
                                    (
                                        1,
                                        debit_lines[0].id,
                                        {"debit": debit_lines[0].debit + delta_balance},
                                    ),
                                    (
                                        1,
                                        credit_lines[0].id,
                                        {
                                            "credit": credit_lines[0].credit
                                            + delta_balance
                                        },
                                    ),
                                ]
                            }
                        )
        return payments

    @_debug.perf.timed
    def _post_payments(self, to_process, edit_mode=False):
        _debug.lifecycle("_post_payments", records=self)
        payments = self.env["account.payment"]
        for vals in to_process:
            payments |= vals["payment"]
        payments.with_context(skip_sale_auto_invoice_send=True).action_post()

    @_debug.perf.timed
    def _reconcile_payments(self, to_process, edit_mode=False):
        domain = [
            ("parent_state", "=", "posted"),
            (
                "account_type",
                "in",
                self.env["account.payment"]._get_valid_payment_account_types(),
            ),
            ("reconciled", "=", False),
        ]
        for vals in to_process:
            payment = vals["payment"]
            payment_lines = payment.move_id.line_ids.filtered_domain(domain)
            lines = vals["to_reconcile"]
            extra_context = (
                {"forced_rate_from_register_payment": vals["rate"]}
                if "rate" in vals
                else {}
            )

            _debug.pipeline(
                "_reconcile_payments_against",
                payment=payment,
                payment_lines=payment_lines,
                lines=lines,
                accounts=payment_lines.account_id,
                rate=vals.get("rate"),
            )
            for account in payment_lines.account_id:
                (payment_lines + lines).with_context(**extra_context).filtered_domain(
                    [
                        ("account_id", "=", account.id),
                        ("reconciled", "=", False),
                    ]
                ).reconcile()
            lines.move_id.matched_payment_ids = [Command.link(payment.id)]

    def _get_payable_batches(self):
        batches = []
        for batch in self.batches:
            batch_account = self._get_batch_account(batch)
            if self.require_partner_bank_account and (
                not batch_account or not batch_account.allow_out_payment
            ):
                continue
            batches.append(batch)

        if _debug.logic.enabled:
            _debug.logic(
                "payable_batches_filtered",
                register=self,
                batches=len(self.batches),
                payable=len(batches),
                require_partner_bank=self.require_partner_bank_account,
            )
        if not batches:
            raise UserError(
                _(
                    "To record payments with %(payment_method)s, the recipient bank account must be manually validated. You should go on the partner bank account in order to validate it.",
                    payment_method=self.payment_channel_id.name,
                )
            )
        return batches

    def _get_single_payment_to_process(self, first_batch_result):
        payment_vals = self._create_payment_vals_from_wizard(first_batch_result)
        to_process_values = {
            "create_vals": payment_vals,
            "to_reconcile": first_batch_result["lines"],
            "batch": first_batch_result,
        }

        if (
            self.writeoff_is_exchange_account
            and self.currency_id == self.company_currency_id
        ):
            total_batch_residual = sum(
                first_batch_result["lines"].mapped("amount_residual_currency")
            )
            to_process_values["rate"] = (
                abs(total_batch_residual / self.amount) if self.amount else 0.0
            )
        return to_process_values

    def _split_batches_per_move(self, batches, lines_to_pay):
        new_batches = []
        for batch_result in batches:
            sub_batches = {}
            for line in batch_result["lines"]:
                if line not in lines_to_pay:
                    continue
                if line.move_id.id in sub_batches:
                    sub_batches[line.move_id.id]["lines"] += line
                else:
                    sub_batches[line.move_id.id] = {
                        **batch_result,
                        "payment_values": {
                            **batch_result["payment_values"],
                            "payment_type": "inbound"
                            if line.balance > 0
                            else "outbound",
                        },
                        "lines": line,
                    }
            new_batches.extend(sub_batches.values())
        _debug.pipeline(
            "batches_split_per_move",
            batches=len(batches),
            new_batches=len(new_batches),
            lines_to_pay=lines_to_pay,
        )
        return new_batches

    def _get_batched_payments_to_process(self, batches):
        lines_to_pay = (
            self._get_total_amounts_to_pay(batches)["lines"]
            if self.installments_mode in ("next", "overdue", "before_date")
            else self.line_ids
        )
        _debug.logic(
            "batched_payments_scope",
            register=self,
            installments_mode=self.installments_mode,
            group_payment=self.group_payment,
            lines_to_pay=lines_to_pay,
        )
        if not self.group_payment:
            batches = self._split_batches_per_move(batches, lines_to_pay)

        to_process = []
        filtered_batches = []
        for batch_result in batches:
            filtered_lines = batch_result["lines"] & lines_to_pay
            if not filtered_lines:
                continue
            batch_result = {**batch_result, "lines": filtered_lines}
            filtered_batches.append(batch_result)
            to_process.append(
                {
                    "create_vals": self._create_payment_vals_from_batch(batch_result),
                    "to_reconcile": batch_result["lines"],
                    "batch": batch_result,
                }
            )
        _debug.pipeline(
            "batched_payments_prepared",
            register=self,
            batches=len(batches),
            kept_batches=len(filtered_batches),
        )
        return filtered_batches, to_process

    @_debug.perf.timed
    def _create_payments(self):
        self.check_singleton()
        batches = self._get_payable_batches()

        first_batch_result = batches[0]
        edit_mode = self.can_edit_wizard and (
            len(first_batch_result["lines"]) == 1 or self.group_payment
        )

        if edit_mode:
            to_process = [self._get_single_payment_to_process(first_batch_result)]
        else:
            batches, to_process = self._get_batched_payments_to_process(batches)
        if _debug.logic.enabled:
            _debug.logic(
                "_create_payments",
                register=self,
                edit_mode=edit_mode,
                group=self.group_payment,
                installments=self.installments_mode,
                batches=len(batches),
                to_process=len(to_process),
            )

        lines = sum(
            (batch_result["lines"] for batch_result in batches),
            self.env["account.move.line"],
        )
        from_sibling_companies = self._is_from_sibling_companies(lines)
        wizard = self.sudo() if from_sibling_companies else self

        payments = wizard.with_context(clean_context(self.env.context))._init_payments(
            to_process, edit_mode=edit_mode
        )
        wizard._post_payments(to_process, edit_mode=edit_mode)
        wizard._reconcile_payments(to_process, edit_mode=edit_mode)
        return payments.sudo(flag=False)

    def _extract_next_payment_date_from_context(self):
        if active_domain := self.env.context.get("active_domain"):
            for domain_elem in active_domain:
                if (
                    isinstance(domain_elem, (list, tuple))
                    and domain_elem[0] == "next_payment_date"
                    and len(domain_elem) == 3
                    and isinstance(domain_elem[2], str)
                ):
                    return fields.Date.to_date(domain_elem[2])
        return False

    @_debug.perf.timed
    def action_create_payments(self):
        _debug.lifecycle("action_create_payments", records=self)
        _debug.logic(
            "register_draft_mode",
            register=self,
            on_draft=self.is_register_payment_on_draft,
        )
        if self.is_register_payment_on_draft:
            self.payment_difference_handling = "open"
        payments = self._create_payments()
        _debug.pipeline(
            "payments_registered",
            register=self,
            payment=payments,
            dont_redirect=bool(self.env.context.get("dont_redirect_to_payments")),
        )

        if self.env.context.get("dont_redirect_to_payments") or not payments.has_access(
            "read"
        ):
            return True

        action = {
            "name": _("Payments"),
            "type": "ir.actions.act_window",
            "res_model": "account.payment",
            "context": {"create": False},
        }
        if len(payments) == 1:
            action.update(
                {
                    "view_mode": "form",
                    "res_id": payments.id,
                }
            )
        else:
            action.update(
                {
                    "view_mode": "list,form",
                    "domain": [("id", "in", payments.ids)],
                }
            )
        return action

    def _get_batch_account(self, batch_result):
        partner_bank_id = batch_result["payment_values"]["partner_bank_id"]
        available_partner_banks = self._get_batch_available_partner_banks(
            batch_result, self.journal_id
        )
        if partner_bank_id and partner_bank_id in available_partner_banks.ids:
            return self.env["res.partner.bank"].browse(partner_bank_id)
        else:
            return available_partner_banks[:1]

    @_debug.perf.timed
    def action_view_untrusted_bank_accounts(self):
        _debug.lifecycle("action_view_untrusted_bank_accounts", records=self)
        self.check_singleton()
        _debug.logic(
            "untrusted_banks_view_chosen",
            register=self,
            banks=self.untrusted_bank_ids,
        )
        if len(self.untrusted_bank_ids) == 1:
            action = {
                "view_mode": "form",
                "res_model": "res.partner.bank",
                "type": "ir.actions.act_window",
                "res_id": self.untrusted_bank_ids.id,
                "views": [
                    [
                        self.env.ref(
                            "account.view_partner_bank_form_inherit_account"
                        ).id,
                        "form",
                    ]
                ],
            }
        else:
            action = {
                "type": "ir.actions.act_window",
                "res_model": "res.partner.bank",
                "views": [
                    [False, "list"],
                    [
                        self.env.ref(
                            "account.view_partner_bank_form_inherit_account"
                        ).id,
                        "form",
                    ],
                ],
                "domain": [["id", "in", self.untrusted_bank_ids.ids]],
            }

        return action

    @_debug.perf.timed
    def action_view_missing_account_partners(self):
        _debug.lifecycle("action_view_missing_account_partners", records=self)
        self.check_singleton()
        vals = {}
        if len(self.missing_account_partners) > 1:
            listview_id = self.env.ref("account.partner_missing_account_list_view").id
            vals["views"] = [(listview_id, "list"), (False, "form")]
        return self.missing_account_partners._get_records_action(**vals)

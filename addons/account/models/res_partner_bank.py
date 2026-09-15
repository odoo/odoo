import base64
from collections import defaultdict
from urllib.parse import urlencode

import werkzeug.exceptions

from odoo import SUPERUSER_ID, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.libs.debug_log import DebugLog
from odoo.tools import SQL
from odoo.tools.image import image_data_uri

from odoo.addons.base.models.res_bank import sanitize_account_number

_debug = DebugLog(__name__)

MONEY_TRANSFER_SERVICES = {
    "967": "Wise",
    "977": "Paynovate",
    "974": "PPS EU SA",
}


class ResPartnerBank(models.Model):
    _name = "res.partner.bank"
    _inherit = ["res.partner.bank", "mixin.mail.thread", "mixin.mail.activity"]

    journal_id = fields.One2many(
        comodel_name="account.journal",
        inverse_name="bank_account_id",
        string="Account Journal",
        readonly=True,
        domain=[("type", "=", "bank")],
        check_company=True,
        help="The accounting journal corresponding to this bank account.",
    )
    has_iban_warning = fields.Boolean(
        compute="_compute_display_account_warning",
        store=True,
        help="Technical field used to display a warning if the IBAN country is different than the holder country.",
    )
    partner_country_name = fields.Char(related="partner_id.country_id.name")
    has_money_transfer_warning = fields.Boolean(
        compute="_compute_display_account_warning",
        store=True,
        help="Technical field used to display a warning if the account is a transfer service account.",
    )
    money_transfer_service = fields.Char(compute="_compute_money_transfer_service")
    partner_supplier_rank = fields.Integer(related="partner_id.supplier_rank")
    partner_customer_rank = fields.Integer(related="partner_id.customer_rank")
    related_moves = fields.One2many(
        comodel_name="account.move",
        inverse_name="partner_bank_id",
    )

    bank_id = fields.Many2one(tracking=True)
    active = fields.Boolean(tracking=True)
    acc_number = fields.Char(tracking=True)
    acc_holder_name = fields.Char(tracking=True)
    clearing_number = fields.Char(tracking=True)
    partner_id = fields.Many2one(tracking=True)
    user_has_group_validate_bank_account = fields.Boolean(
        compute="_compute_user_has_group_validate_bank_account"
    )
    allow_out_payment = fields.Boolean(
        tracking=True,
        help="Sending fake invoices with a fraudulent account number is a common phishing practice. "
        "To protect yourself, always verify new bank account numbers, preferably by calling the vendor, as phishing "
        "usually happens when their emails are compromised. Once verified, you can activate the ability to send money.",
    )
    currency_id = fields.Many2one(tracking=True)
    lock_trust_fields = fields.Boolean(compute="_compute_lock_trust_fields")
    duplicate_bank_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_duplicate_bank_partner_ids",
    )

    @api.constrains("journal_id")
    @_debug.perf.timed
    def _check_journal_id(self):
        for bank in self:
            if len(bank.journal_id) > 1:
                raise ValidationError(
                    self.env._("A bank account can belong to only one journal.")
                )

    @_debug.perf.timed
    def _check_allow_out_payment(self):
        for bank in self:
            if bank.allow_out_payment and not bank._can_user_trust():
                raise ValidationError(
                    self.env._(
                        "You do not have the right to trust or un-trust a bank account."
                    )
                )

    @api.depends("acc_number")
    @_debug.perf.timed
    def _compute_duplicate_bank_partner_ids(self):
        id2duplicates = dict(
            self.env.execute_query(
                SQL(
                    """
                SELECT this.id,
                       ARRAY_AGG(other.partner_id)
                  FROM res_partner_bank this
             LEFT JOIN res_partner_bank other ON this.acc_number = other.acc_number
                                             AND this.id != other.id
                                             AND other.active = TRUE
                 WHERE this.id = ANY(%(ids)s)
                 AND other.partner_id IS NOT NULL
                   AND this.active = TRUE
                   AND (
                        ((this.company_id = other.company_id) OR (this.company_id IS NULL AND other.company_id IS NULL))
                        OR
                        other.company_id IS NULL
                        )
              GROUP BY this.id
            """,
                    ids=self.ids,
                )
            )
        )
        _debug.pipeline(
            "duplicate_accounts_read",
            banks=self,
            with_duplicates=len(id2duplicates),
        )
        for bank in self:
            duplicate_record = id2duplicates.get(bank._origin.id) or []
            bank.duplicate_bank_partner_ids = (
                self.env["res.partner"].browse(duplicate_record)
                if duplicate_record
                else False
            )

    @api.depends(
        "partner_id.country_id", "sanitized_acc_number", "allow_out_payment", "acc_type"
    )
    @_debug.perf.timed
    def _compute_display_account_warning(self):
        for bank in self:
            if (
                bank.allow_out_payment
                or not bank.sanitized_acc_number
                or bank.acc_type != "iban"
            ):
                bank.has_iban_warning = False
                bank.has_money_transfer_warning = False
                continue
            bank_country = bank.sanitized_acc_number[:2]
            bank.has_iban_warning = (
                bank.partner_id.country_id
                and bank_country != bank.partner_id.country_id.code
            )
            bank.has_money_transfer_warning = bool(bank._get_money_transfer_service())

    @api.depends("sanitized_acc_number")
    def _compute_money_transfer_service(self):
        for bank in self:
            bank.money_transfer_service = bank._get_money_transfer_service() or False

    def _get_money_transfer_service(self):
        self.check_singleton()
        sanitized = self.sanitized_acc_number
        if not sanitized or sanitized[:2] != "BE":
            return None
        return self._get_money_transfer_services().get(sanitized[4:7])

    def _get_money_transfer_services(self):
        return MONEY_TRANSFER_SERVICES

    @api.depends("acc_number")
    @api.depends_context("uid")
    def _compute_user_has_group_validate_bank_account(self):
        for bank in self:
            bank.user_has_group_validate_bank_account = bank._can_user_trust()

    @api.depends("allow_out_payment")
    def _compute_lock_trust_fields(self):
        for bank in self:
            bank.lock_trust_fields = bool(bank._origin) and bool(bank.allow_out_payment)

    @_debug.perf.timed
    def _prepare_qr_code_vals(
        self,
        amount,
        free_communication,
        structured_communication,
        currency,
        debtor_partner,
        qr_method=None,
        silent_errors=True,
    ):
        if not self:
            _debug.logic("qr_skipped", reason="no_bank_account")
            return None

        self.check_singleton()
        if not currency:
            raise UserError(
                self.env._(
                    "Currency must always be provided in order to generate a QR-code"
                )
            )

        available_qr_methods = self.get_available_qr_methods_in_sequence()
        if qr_method:
            candidate_methods = [(qr_method, dict(available_qr_methods)[qr_method])]
        else:
            candidate_methods = available_qr_methods
        _debug.logic(
            "qr_candidates_resolved",
            bank=self,
            forced=qr_method,
            available=len(available_qr_methods),
            candidates=len(candidate_methods),
        )
        for candidate_method, candidate_name in candidate_methods:
            error_message = self._get_error_messages_for_qr(
                candidate_method, debtor_partner, currency
            )
            if not error_message:
                error_message = self._check_for_qr_code_errors(
                    candidate_method,
                    amount,
                    currency,
                    debtor_partner,
                    free_communication,
                    structured_communication,
                )

                if not error_message:
                    _debug.logic(
                        "qr_method_chosen", bank=self, qr_method=candidate_method
                    )
                    return {
                        "qr_method": candidate_method,
                        "amount": amount,
                        "currency": currency,
                        "debtor_partner": debtor_partner,
                        "free_communication": free_communication,
                        "structured_communication": structured_communication,
                    }

            _debug.logic(
                "qr_method_rejected",
                bank=self,
                qr_method=candidate_method,
                raises=not silent_errors,
            )
            if not silent_errors:
                raise UserError(
                    self.env._(
                        "The following error prevented '%(candidate)s' QR-code to be generated though it was detected as eligible: ",
                        candidate=candidate_name,
                    )
                    + error_message
                )

        _debug.logic("qr_no_method", bank=self, candidates=len(candidate_methods))
        return None

    def prepare_qr_code_url(
        self,
        amount,
        free_communication,
        structured_communication,
        currency,
        debtor_partner,
        qr_method=None,
        silent_errors=True,
    ):
        vals = self._prepare_qr_code_vals(
            amount,
            free_communication,
            structured_communication,
            currency,
            debtor_partner,
            qr_method,
            silent_errors,
        )
        if vals:
            return self._get_qr_code_url(**vals)
        return None

    def prepare_qr_code_base64(
        self,
        amount,
        free_communication,
        structured_communication,
        currency,
        debtor_partner,
        qr_method=None,
        silent_errors=True,
    ):
        vals = self._prepare_qr_code_vals(
            amount,
            free_communication,
            structured_communication,
            currency,
            debtor_partner,
            qr_method,
            silent_errors,
        )
        if vals:
            return self._get_qr_code_base64(**vals)
        return None

    def _prepare_qr_payload(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):
        return None

    def _prepare_qr_rendering_params(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):
        raise NotImplementedError

    def _get_qr_code_url(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):
        params = self._prepare_qr_rendering_params(
            qr_method,
            amount,
            currency,
            debtor_partner,
            free_communication,
            structured_communication,
        )
        return "/report/barcode/?" + urlencode(params) if params else None

    def _get_qr_code_base64(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):
        params = self._prepare_qr_rendering_params(
            qr_method,
            amount,
            currency,
            debtor_partner,
            free_communication,
            structured_communication,
        )
        _debug.logic("qr_params_resolved", qr_method=qr_method, has_params=bool(params))
        if params:
            try:
                barcode = self.env["ir.actions.report"].prepare_barcode(**params)
            except ValueError, AttributeError:
                _debug.logic("qr_barcode_failed", qr_method=qr_method)
                raise werkzeug.exceptions.HTTPException(
                    description="Cannot convert into barcode."
                ) from None
            return image_data_uri(base64.b64encode(barcode))
        return None

    @api.model
    def _get_available_qr_methods(self):
        return []

    @api.model
    def get_available_qr_methods_in_sequence(self):
        all_available = self._get_available_qr_methods()
        all_available.sort(key=lambda x: x[2])
        return [(code, name) for (code, name, sequence) in all_available]

    def _get_error_messages_for_qr(self, qr_method, debtor_partner, currency):
        return

    def _check_for_qr_code_errors(
        self,
        qr_method,
        amount,
        currency,
        debtor_partner,
        free_communication,
        structured_communication,
    ):
        return

    def _can_user_trust(self):
        return (
            super()._can_user_trust()
            and (
                self.env.su
                or self.env.user.has_group("account.group_validate_bank_account")
                or self.env.user.has_group("base.group_system")
            )
            and (
                self.env.user.id != SUPERUSER_ID
                or self.env.context.get("install_mode")
                or tools.config["test_enable"]
            )
        )

    @_debug.perf.timed
    def action_view_business_doc(self):
        _debug.lifecycle("action_view_business_doc", records=self)
        return self._get_records_action()

    @api.model_create_multi
    @_debug.perf.timed
    def create(self, vals_list):
        if _debug.lifecycle.enabled:
            _debug.lifecycle(
                "create",
                model=self._name,
                count=len(vals_list),
                fields=sorted({key for vals in vals_list for key in vals}),
            )
        to_trust = []
        for vals in vals_list:
            to_trust.append(vals.get("allow_out_payment"))
            vals["allow_out_payment"] = False

        self._raise_if_archived_account_exists(vals_list)

        accounts = super().create(vals_list)
        if _debug.logic.enabled:
            _debug.logic(
                "trust_requested",
                accounts=accounts,
                requested=sum(1 for trust in to_trust if trust),
            )
        for account, trust in zip(accounts, to_trust, strict=True):
            if trust and account._can_user_trust():
                account.allow_out_payment = True
            msg = self.env._(
                "Bank Account %s created",
                account._get_html_link(title=f"#{account.id}"),
            )
            account.partner_id._message_log(body=msg)
        return accounts

    @_debug.perf.timed
    def _raise_if_archived_account_exists(self, vals_list):
        pairs = [
            (vals["partner_id"], vals["acc_number"])
            for vals in vals_list
            if vals.get("partner_id") and vals.get("acc_number")
        ]
        _debug.logic(
            "archived_check_scope",
            pairs=len(pairs),
            vals=len(vals_list),
            skipped=not pairs,
        )
        if not pairs:
            return
        archived = self.env["res.partner.bank"].search(
            [
                ("active", "=", False),
                ("partner_id", "in", [partner_id for partner_id, _acc in pairs]),
                ("acc_number", "in", [acc for _partner_id, acc in pairs]),
            ]
        )
        archived_by_key = {
            (bank.partner_id.id, bank.sanitized_acc_number): bank for bank in archived
        }
        for partner_id, acc_number in pairs:
            existing = archived_by_key.get(
                (partner_id, sanitize_account_number(acc_number))
            )
            if existing:
                _debug.logic(
                    "archived_account_conflict",
                    bank=existing,
                    partner_id=partner_id,
                    archived=len(archived),
                )
                raise UserError(
                    self.env._(
                        "A bank account with Account Number %(number)s already exists"
                        " for Partner %(partner)s, but is archived. Please unarchive"
                        " it instead.",
                        number=acc_number,
                        partner=existing.partner_id.name,
                    )
                )

    @_debug.perf.timed
    def write(self, vals):
        _debug.lifecycle("write", records=self, fields=sorted(vals))
        account_initial_values = defaultdict(dict)
        tracking_fields = [
            field_name
            for field_name in vals
            if getattr(self._fields[field_name], "tracking", False)
            and not self._fields[field_name].related
        ]
        fields_definition = self.fields_get(tracking_fields)

        for account in self:
            for field in tracking_fields:
                account_initial_values[account][field] = account[field]

        trusted_accounts = self.filtered(lambda x: x.lock_trust_fields)
        if not trusted_accounts:
            should_allow_changes = True
        else:
            should_allow_changes = self.env.su or (
                "allow_out_payment" in vals and vals["allow_out_payment"] is False
            )

        _debug.logic(
            "trust_lock_decided",
            banks=self,
            trusted=trusted_accounts,
            allow_changes=should_allow_changes,
            tracking_fields=len(tracking_fields),
        )
        lock_fields = {"acc_number", "sanitized_acc_number", "partner_id", "acc_type"}
        if not should_allow_changes and any(
            account[fname]
            != account._fields[fname].convert_to_record(
                account._fields[fname].convert_to_cache(vals[fname], account),
                account,
            )
            for fname in lock_fields & set(vals)
            for account in trusted_accounts
        ):
            _debug.logic(
                "trusted_account_edit_blocked", banks=self, trusted=trusted_accounts
            )
            raise UserError(
                self.env._(
                    "You cannot modify the account number or partner of an account that has been trusted."
                )
            )

        if "allow_out_payment" in vals and any(
            not bank._can_user_trust() for bank in self
        ):
            _debug.logic("trust_rights_missing", banks=self)
            raise UserError(
                self.env._("You do not have the rights to trust or un-trust accounts.")
            )

        res = super().write(vals)

        if "allow_out_payment" in vals:
            self._check_allow_out_payment()

        for account, initial_values in account_initial_values.items():
            tracking_value_ids = account._mail_track(fields_definition, initial_values)[
                1
            ]
            if tracking_value_ids:
                msg = self.env._(
                    "Bank Account %s updated",
                    account._get_html_link(title=f"#{account.id}"),
                )
                account.partner_id._message_log(
                    body=msg, tracking_value_ids=tracking_value_ids
                )
                if "partner_id" in initial_values:
                    initial_values["partner_id"]._message_log(
                        body=msg, tracking_value_ids=tracking_value_ids
                    )
        return res

    @_debug.perf.timed
    def unlink(self):
        _debug.lifecycle("unlink", unlink=self)
        for account in self:
            msg = self.env._(
                "Bank Account %(link)s with number %(number)s archived",
                link=account._get_html_link(title=f"#{account.id}"),
                number=account.acc_number,
            )
            account.partner_id._message_log(body=msg)
        return super().unlink()

    @api.model
    @_debug.perf.timed
    def default_get(self, fields):
        _debug.lifecycle("default_get", records=self)
        if "acc_number" not in fields:
            return super().default_get(fields)

        default_acc_number = self.env.context.get(
            "default_acc_number", False
        ) or self.env.context.get("default_name", False)
        return super(
            ResPartnerBank, self.with_context(default_acc_number=default_acc_number)
        ).default_get(fields)

    @api.depends("allow_out_payment", "acc_number", "bank_id")
    @api.depends_context("display_account_trust")
    def _compute_display_name(self):
        super()._compute_display_name()
        if self.env.context.get("display_account_trust"):
            for acc in self:
                trusted_label = (
                    self.env._("trusted")
                    if acc.allow_out_payment
                    else self.env._("untrusted")
                )
                acc_number = acc.acc_number or ""
                if acc.bank_id:
                    name = f"{acc_number} - {acc.bank_id.name} ({trusted_label})"
                else:
                    name = f"{acc_number} ({trusted_label})"
                acc.display_name = name

import re
from typing import Any, Self

from odoo import api, fields, models
from odoo.api import ValuesType
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog
from odoo.tools import _, clean_context

_debug = DebugLog(__name__)


def sanitize_account_number(acc_number: str | bool) -> str | bool:
    if acc_number:
        return re.sub(r"\W+", "", acc_number).upper()
    return False


class ResPartnerBank(models.Model):
    _name = "res.partner.bank"
    _rec_name = "acc_number"
    _description = "Bank Accounts"
    _order = "sequence, id"
    _check_company_domain = models.check_company_domain_parent_of

    @api.model
    def _get_account_types_supported(self) -> list[tuple[str, str]]:
        return [("bank", _("Normal"))]

    active = fields.Boolean(default=True)
    acc_type = fields.Selection(
        selection=lambda x: x.env["res.partner.bank"]._get_account_types_supported(),
        string="Type",
        compute="_compute_acc_type",
        help="Bank account type: Normal or IBAN. Inferred from the bank account number.",
    )
    acc_number = fields.Char(
        string="Account Number",
        search="_search_acc_number",
        required=True,
    )
    clearing_number = fields.Char()
    sanitized_acc_number = fields.Char(
        string="Sanitized Account Number",
        compute="_compute_sanitized_acc_number",
        store=True,
        readonly=True,
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Account Holder",
        index=True,
        required=True,
        domain=["|", ("is_company", "=", True), ("parent_id", "=", False)],
        ondelete="cascade",
    )
    company_id = fields.Many2one(  # noqa: E8529  UNIQUE (sanitized_acc_number, company_id) partial
        comodel_name="res.company",
        related="partner_id.company_id",
        string="Company",
        store=True,
        readonly=True,
    )
    country_code = fields.Char(
        related="partner_id.country_code",
        string="Country Code",
    )
    acc_holder_name = fields.Char(
        string="Account Holder Name",
        compute="_compute_acc_holder_name",
        store=True,
        readonly=False,
        help="Account holder name, in case it is different than the name of the Account Holder",
    )
    currency_id = fields.Many2one(comodel_name="res.currency")
    bank_id = fields.Many2one(comodel_name="res.bank")
    bank_name = fields.Char(
        related="bank_id.name",
        readonly=False,
    )
    bank_bic = fields.Char(
        related="bank_id.bic",
        readonly=False,
    )
    sequence = fields.Integer(default=10)
    note = fields.Text(string="Notes")
    allow_out_payment = fields.Boolean(
        string="Send Money",
        default=False,
        copy=False,
        readonly=False,
        help="This account can be used for outgoing payments",
    )
    color = fields.Integer(compute="_compute_color")

    _unique_number = models.UniqueIndex(
        "(sanitized_acc_number, company_id) "
        "WHERE sanitized_acc_number IS NOT NULL AND company_id IS NOT NULL",
        "An account number names one account, so a company records it once. "
        "This number is already held by another contact in the same company.",
    )

    @api.model_create_multi
    def create(self, vals_list: list[ValuesType]) -> Self:
        _debug.lifecycle(
            "bank_account_create",
            count=len(vals_list),
            partners=sorted({vals.get("partner_id") or 0 for vals in vals_list}),
        )
        return super().create([self._normalize_vals(vals) for vals in vals_list])

    def write(self, vals: dict[str, Any]) -> bool:
        _debug.lifecycle("bank_account_write", count=len(self), fields=list(vals))
        return super().write(self._normalize_vals(vals))

    def unlink(self) -> bool:
        _debug.lifecycle("bank_account_archived", accounts=self.ids, by="unlink")
        self.action_archive()
        return True

    @api.depends("acc_number")
    def _compute_sanitized_acc_number(self) -> None:
        for bank in self:
            bank.sanitized_acc_number = sanitize_account_number(bank.acc_number)

    @api.depends("acc_number")
    def _compute_acc_type(self) -> None:
        for bank in self:
            bank.acc_type = self._get_acc_type(bank.acc_number)

    @api.depends("partner_id")
    def _compute_acc_holder_name(self) -> None:
        for bank in self:
            bank.acc_holder_name = bank.partner_id.name

    @api.depends("acc_number", "bank_id.name")
    def _compute_display_name(self) -> None:
        for acc in self:
            acc_number = acc.acc_number or ""
            acc.display_name = (
                f"{acc_number} - {acc.bank_id.name}" if acc.bank_id else acc_number
            )

    @api.depends("allow_out_payment")
    def _compute_color(self) -> None:
        for bank in self:
            bank.color = 10 if bank.allow_out_payment else 1

    def _search_acc_number(self, operator: str, value: str | list[str]) -> list:
        if operator in ("in", "not in"):
            value = [sanitize_account_number(i) for i in value]
        else:
            value = sanitize_account_number(value)
        _debug.logic(
            "acc_number_search",
            operator=operator,
            values=len(value) if isinstance(value, list) else 1,
        )
        return [("sanitized_acc_number", operator, value)]

    def action_archive_bank(self) -> dict[str, str]:
        self.check_singleton()
        _debug.lifecycle("bank_account_archived", account=self.id, by="action")
        self.action_archive()
        return {"type": "ir.actions.client", "tag": "reload"}

    def _get_or_create_bank_account(
        self,
        account_number,
        partner,
        company,
        *,
        allow_company_account_creation=False,
        extra_create_vals=None,
        revive_archived_match=True,
    ):
        bank_account = (
            self.env["res.partner.bank"]
            .sudo()
            .with_context(active_test=False)
            .search(
                [
                    ("acc_number", "=", account_number),
                    ("partner_id", "child_of", partner.commercial_partner_id.id),
                ]
            )
        )
        _debug.logic(
            "bank_account_lookup",
            partner=partner.id,
            found=len(bank_account),
            active=len(bank_account.filtered("active")),
        )
        if (
            revive_archived_match
            and bank_account
            and not bank_account.filtered("active")
        ):
            revived = bank_account.filtered(lambda b: b.partner_id == partner)
            _debug.lifecycle(
                "bank_account_revived", partner=partner.id, accounts=revived.ids
            )
            revived.sudo(False).action_unarchive()
        if not bank_account:
            if (
                not allow_company_account_creation
                and partner.id in self.env["res.company"]._get_company_partner_ids()
            ):
                _debug.logic(
                    "bank_account_creation_refused",
                    partner=partner.id,
                    reason="company_partner",
                )
                raise UserError(
                    _(
                        "Please add your own bank account manually: %(account_number)s (%(partner)s)",
                        account_number=account_number,
                        partner=partner.display_name,
                    )
                )
            bank_account = (
                self.env["res.partner.bank"]
                .with_context(clean_context(self.env.context))
                .create(
                    {
                        **(extra_create_vals or {}),
                        "acc_number": account_number,
                        "partner_id": partner.id,
                        "allow_out_payment": False,
                    }
                )
            )
            _debug.lifecycle(
                "bank_account_created", partner=partner.id, account=bank_account.id
            )
        usable = bank_account.filtered_domain(
            [
                *self.env["res.partner.bank"]._check_company_domain(company),
                ("active", "=", True),
            ]
        )
        _debug.logic(
            "bank_account_resolved",
            partner=partner.id,
            company=company.id if company else False,
            candidates=len(bank_account),
            usable=len(usable),
        )
        return usable.sorted(lambda b: b.partner_id != partner).sudo(False)[:1]

    @api.model
    def _get_acc_type(self, acc_number: str) -> str:
        return "bank"

    def _normalize_vals(self, vals: ValuesType) -> ValuesType:
        if "acc_number" not in vals and "sanitized_acc_number" in vals:
            _debug.logic("acc_number_taken_from_sanitized")
            vals = dict(vals)
            vals["acc_number"] = vals.pop("sanitized_acc_number")
        if "acc_number" in vals:
            vals = {
                **vals,
                "sanitized_acc_number": sanitize_account_number(vals["acc_number"]),
            }
        return vals

    def _can_user_trust(self):
        self.check_singleton()
        return True

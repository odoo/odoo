from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.fields import Domain
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class HrExpense(models.Model):
    _name = "hr.expense"
    _inherit = ["hr.expense", "mixin.extract"]

    _extract_document_type = "receipt"

    extract_can_be_read = fields.Boolean(compute="_compute_extract_can_be_read")

    @api.depends("state", "extract_state")
    def _compute_extract_can_be_read(self) -> None:
        for expense in self:
            expense.extract_can_be_read = expense.state == "draft" and (
                expense.extract_state in ("none", "failed", "partial")
            )

    def _update_from_extraction(self, result) -> None:
        self.check_singleton()
        super()._update_from_extraction(result)

        values = result.flat()
        writes = {}

        if merchant := values.get("merchant_name"):
            if self._extract_name_is_untouched():
                writes["name"] = merchant
            if _debug.logic.enabled and "name" not in writes:
                _debug.logic(
                    "receipt_field_kept",
                    reason="name_edited_by_a_person",
                    expense=self,
                    field="name",
                )

        if date := values.get("date"):
            if self._extract_date_is_untouched():
                writes["date"] = date
            if _debug.logic.enabled and "date" not in writes:
                _debug.logic(
                    "receipt_field_kept",
                    reason="date_edited_by_a_person",
                    expense=self,
                    field="date",
                )

        writes.update(self._get_extract_amount_values(values, writes.get("date")))

        _debug.pipeline(
            "receipt_applied",
            expense=self,
            read_fields=len(values),
            written_fields=sorted(writes),
        )
        if writes:
            self.write(writes)

    def _extract_name_is_untouched(self) -> bool:
        self.check_singleton()
        user = self.employee_id.user_id or self.env.user
        untitled = self.with_user(user)._get_untitled_expense_name("").strip()
        return untitled in (self.name or "")

    def _extract_date_is_untouched(self) -> bool:
        self.check_singleton()
        return not self.date or self.date == fields.Date.context_today(
            self, self.create_date
        )

    def _get_extract_amount_values(self, values, date=None) -> dict:
        self.check_singleton()
        total = values.get("total")
        if not total:
            _debug.logic("receipt_amount_absent", reason="no_total_read", expense=self)
            return {}

        writes = {
            "quantity": 1,
            "price_unit": total,
            "total_amount_currency": total,
            "total_amount": total,
        }

        currency = self._get_extract_currency(values.get("currency"))
        _debug.logic(
            "receipt_currency",
            expense=self,
            read=values.get("currency"),
            resolved=currency,
            untouched=self._extract_currency_is_untouched(),
        )
        if currency and self._extract_currency_is_untouched():
            writes["currency_id"] = currency.id
            if currency != self.company_currency_id:
                writes["total_amount"] = currency._convert(
                    total,
                    self.company_currency_id,
                    company=self.company_id,
                    date=date or self.date,
                )
        return writes

    def _extract_currency_is_untouched(self) -> bool:
        self.check_singleton()
        return not self.currency_id or self.currency_id == self.company_currency_id

    def _get_extract_currency(self, name: str | None):
        if not name:
            return None
        name = name.strip()
        currencies = self.env["res.currency"].with_context(active_test=False)
        for operator in ("=ilike", "ilike"):
            matched = currencies.search(
                Domain.OR(
                    [
                        Domain("currency_unit_label", operator, name),
                        Domain("name", operator, name),
                        Domain("symbol", operator, name),
                    ]
                )
            )
            if len(matched) == 1:
                _debug.logic(
                    "receipt_currency_matched",
                    name=name,
                    operator=operator,
                    currency=matched,
                )
                return matched
        _debug.logic("receipt_currency_unmatched", reason="no_unique_match", name=name)
        return None

    def action_extract_document(self):
        self.check_singleton()
        if not self.extract_can_be_read:
            _debug.logic(
                "receipt_read_refused",
                reason="expense_no_longer_draft",
                expense=self,
                state=self.state,
                extract_state=self.extract_state,
            )
            raise UserError(_("A receipt is read while the expense is still a draft."))
        result = self._extract_document()
        if result is None:
            _debug.logic(
                "receipt_read_absent", reason="no_extraction_result", expense=self
            )
            return False
        _debug.lifecycle(
            "receipt_read",
            expense=self,
            satisfied=result.satisfied,
            missing=len(result.missing),
        )
        if result.satisfied:
            message = _("The receipt was read in full.")
        else:
            message = _(
                "The receipt was read in part. Still missing: %(fields)s",
                fields=", ".join(result.missing) or _("nothing required"),
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": message, "type": "info", "sticky": False},
        }

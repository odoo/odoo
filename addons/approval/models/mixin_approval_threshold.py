import math

from odoo import api, fields, models
from odoo.exceptions import ValidationError

from . import approval_trace as trace

_FLOAT_EQ_ABS_TOL = 1e-6
_FLOAT_EQ_REL_TOL = 1e-9


class MixinApprovalThreshold(models.AbstractModel):
    _name = "mixin.approval.threshold"
    _description = "Approval Threshold Comparison"

    company_id = fields.Many2one(
        comodel_name="res.company",
        compute="_compute_company_id",
        precompute=True,
        store=True,
        index=True,
        readonly=False,
        help="Company this record is scoped to. Empty means it applies to "
        "every company, which is how a shared category carries global "
        "tiers and rules (see approval.request._rule_applies_to_company).",
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        help="Currency this record's amount thresholds are expressed in. "
        "A request's amount is converted into it before any comparison, "
        "so a global tier or rule on a shared category evaluates "
        "correctly across companies with different currencies.",
    )

    condition_field = fields.Selection(
        selection=[
            ("amount", "Amount"),
            ("quantity", "Quantity"),
            ("date_range_days", "Date Range (Days)"),
            ("priority", "Priority"),
        ],
        help="Figure on the request to compare: the amount, converted into this "
        "record's currency, the quantity, the date range in days, or the priority.",
    )
    operator = fields.Selection(
        selection=[
            ("gt", "Greater than"),
            ("gte", "Greater than or equal"),
            ("lt", "Less than"),
            ("lte", "Less than or equal"),
            ("eq", "Equal to"),
            ("neq", "Not equal to"),
            ("between", "Between"),
        ],
        string="Comparison",
        help="How the request's figure compares with the threshold.",
    )
    threshold = fields.Float(
        help="Numeric threshold to compare against, and the lower bound "
        "(inclusive) when the comparison is 'Between'. "
        "For priority: 0=Low, 1=Normal, 2=High, 3=Urgent."
    )
    threshold_max = fields.Float(
        string="Upper Bound (exclusive)",
        help="Only for the 'Between' comparison: the upper bound, exclusive. "
        "0 means unlimited, which is how the highest band is expressed.",
    )

    def _compute_company_id(self) -> None:
        for record in self:
            record.company_id = self.env.company

    @api.depends("company_id")
    def _compute_currency_id(self) -> None:
        for record in self:
            record.currency_id = (
                record.company_id.currency_id or self.env.company.currency_id
            )

    def _convert_request_amount(self, request) -> float:
        self.check_singleton()
        from_currency = request.currency_id
        to_currency = self.currency_id
        if not from_currency or not to_currency or from_currency == to_currency:
            trace.RULES.event(
                "amount_unconverted",
                record=self.id,
                request=request.id,
                amount=request.amount,
                reason="same_currency"
                if from_currency and to_currency
                else "currency_missing",
                from_currency=from_currency.id,
                to_currency=to_currency.id,
            )
            return request.amount
        rate_datetime = request.date or request.date_confirmed
        rate_date = (
            rate_datetime.date() if rate_datetime else fields.Date.context_today(self)
        )
        converted = from_currency._convert(
            request.amount,
            to_currency,
            request.company_id or self.company_id or self.env.company,
            rate_date,
        )
        trace.RULES.event(
            "amount_converted",
            record=self.id,
            request=request.id,
            amount=request.amount,
            converted=converted,
            from_currency=from_currency.id,
            to_currency=to_currency.id,
            rate_date=rate_date,
        )
        return converted

    @staticmethod
    def _intervals_overlap(bounds_a, bounds_b) -> bool:
        lo_a, lo_a_closed, hi_a, hi_a_closed = bounds_a
        lo_b, lo_b_closed, hi_b, hi_b_closed = bounds_b
        if hi_a < lo_b or (hi_a == lo_b and not (hi_a_closed and lo_b_closed)):
            return False
        return not (hi_b < lo_a or (hi_b == lo_a and not (hi_b_closed and lo_a_closed)))

    def _get_field_value(self, request) -> float | None:
        match self.condition_field:
            case "amount":
                return self._convert_request_amount(request)
            case "quantity":
                return request.quantity
            case "priority":
                return int(request.priority)
            case "date_range_days":
                if request.date_start and request.date_end:
                    delta = request.date_end - request.date_start
                    return delta.total_seconds() / 86400
                trace.RULES.event(
                    "condition_value_missing",
                    record=self.id,
                    request=request.id,
                    field=self.condition_field,
                    has_start=bool(request.date_start),
                    has_end=bool(request.date_end),
                )
                return None
            case _:
                trace.RULES.event(
                    "condition_field_unknown",
                    record=self.id,
                    request=request.id,
                    field=self.condition_field,
                )
                return None

    def _compare(self, value: float, threshold: float) -> bool:
        self.check_singleton()
        op = self.operator
        if op == "gt":
            return value > threshold
        if op == "gte":
            return value >= threshold
        if op == "lt":
            return value < threshold
        if op == "lte":
            return value <= threshold
        if op == "eq":
            return math.isclose(
                value,
                threshold,
                rel_tol=_FLOAT_EQ_REL_TOL,
                abs_tol=_FLOAT_EQ_ABS_TOL,
            )
        if op == "neq":
            return not math.isclose(
                value,
                threshold,
                rel_tol=_FLOAT_EQ_REL_TOL,
                abs_tol=_FLOAT_EQ_ABS_TOL,
            )
        if op == "between":
            if value < threshold:
                return False
            return not (self.threshold_max and value >= self.threshold_max)
        trace.REFUSAL.event("unknown_operator", record=self.id, operator=op)
        raise ValidationError(
            self.env._(
                "Unknown operator '%(op)s' on '%(name)s'.",
                op=op,
                name=self.display_name,
            ),
        )

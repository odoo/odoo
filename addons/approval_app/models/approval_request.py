from collections import Counter
from typing import Any, Self

from odoo import api, fields, models
from odoo.exceptions import UserError

from odoo.addons.approval.models import approval_trace as trace

_FORM_LOCKED_FIELDS = frozenset(
    {"date_deadline", "date_planned", "reference", "location"}
)


class ApprovalRequest(models.Model):
    _inherit = "approval.request"

    date_deadline = fields.Datetime()
    date_planned = fields.Datetime()
    location = fields.Char()
    reference = fields.Char()
    has_date = fields.Selection(related="category_id.has_date")
    has_date_deadline = fields.Selection(related="category_id.has_date_deadline")
    has_date_planned = fields.Selection(related="category_id.has_date_planned")
    has_date_range = fields.Selection(related="category_id.has_date_range")
    has_quantity = fields.Selection(related="category_id.has_quantity")
    has_amount = fields.Selection(related="category_id.has_amount")
    has_reference = fields.Selection(related="category_id.has_reference")
    has_partner = fields.Selection(related="category_id.has_partner")
    has_location = fields.Selection(related="category_id.has_location")
    has_document = fields.Selection(related="category_id.has_document")
    document_requirement_ids = fields.One2many(
        related="category_id.document_requirement_ids",
        string="Required Documents",
        help="The category's document requirements, related onto the request "
        "so the Documents page can offer exactly those in the 'Satisfies "
        "Requirement' dropdown beside each attachment.",
    )
    template_id = fields.Many2one(
        comodel_name="approval.template",
        index="btree_not_null",
        copy=False,
        readonly=True,
        help="Template this request was created from (if any)",
    )

    def _check_confirm(self) -> None:
        super()._check_confirm()
        self._check_has_document_has_attachment()
        self._check_category_required_fields()

    def _get_fields_locked(self) -> frozenset[str]:
        return super()._get_fields_locked() | _FORM_LOCKED_FIELDS

    def _get_pending_change_candidates(self) -> frozenset[str]:
        candidates = super()._get_pending_change_candidates()
        if self.has_date != "no" or self.has_date_range != "no":
            candidates |= {"date"}
        return candidates

    def _recent_approved_by_owner(self, limit: int = 10) -> Self:
        self.check_singleton()
        return self._recent_approved_by_category(
            self.category_id,
            self.request_owner_id,
            limit=limit,
        )[self.category_id.id]

    def _recent_approved_by_category(self, categories, owner, limit: int = 10) -> dict:
        by_category: dict[int, list[int]] = {
            category_id: [] for category_id in categories.ids
        }
        if not categories or not owner:
            return {category_id: self.browse() for category_id in by_category}
        with trace.SEARCH.span(
            "recent_approved_by_category",
            categories=len(by_category),
            owner=owner.id,
            limit=limit,
        ) as span:
            candidates = self.search(
                [
                    ("request_owner_id", "=", owner.id),
                    ("category_id", "in", categories.ids),
                    ("state", "=", "approved"),
                ],
                order="date_confirmed desc",
                limit=limit * len(categories),
            )
            for request in candidates:
                bucket = by_category[request.category_id.id]
                if len(bucket) < limit:
                    bucket.append(request.id)
            span["n"] = len(candidates)
            span["truncated"] = len(candidates) == limit * len(by_category)
            span["short"] = sum(1 for ids in by_category.values() if len(ids) < limit)
        return {
            category_id: self.browse(ids) for category_id, ids in by_category.items()
        }

    def _smart_clone_defaults(self, recent=None) -> dict[str, Any]:
        self.check_singleton()
        category = self.category_id
        smart: dict[str, Any] = {}
        if recent is None:
            recent = self._recent_approved_by_owner(limit=10)

        if category.has_amount != "no":
            amounts = [r.amount for r in recent if r.amount]
            if amounts:
                smart["amount"] = sum(amounts) / len(amounts)

        if category.has_partner != "no" and recent:
            partners = recent.mapped("partner_id").filtered(bool)
            if partners:
                smart["partner_id"] = Counter(partners).most_common(1)[0][0].id

        if trace.PREDICTION.on():
            trace.PREDICTION.event(
                "smart_clone_defaults",
                request=self.id,
                category=category.id,
                recent=len(recent),
                inferred=sorted(smart),
                asks_amount=category.has_amount,
                asks_partner=category.has_partner,
            )
        return smart

    def copy_data(self, default: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        explicit = dict(default or {})
        vals_list = super().copy_data(default=explicit)
        recent_by_owner = {
            owner.id: self._recent_approved_by_category(
                self.filtered(lambda r, o=owner: r.request_owner_id == o).category_id,
                owner,
            )
            for owner in self.request_owner_id
        }
        applied = 0
        suppressed = 0
        for source, vals in zip(self, vals_list, strict=True):
            recent = recent_by_owner.get(source.request_owner_id.id, {}).get(
                source.category_id.id, self.browse()
            )
            for key, value in source._smart_clone_defaults(recent).items():
                if key in explicit:
                    suppressed += 1
                    continue
                vals[key] = value
                applied += 1
        trace.CRUD.event(
            "copy_data",
            requests=len(vals_list),
            owners=len(recent_by_owner),
            explicit=sorted(explicit),
            applied=applied,
            suppressed=suppressed,
        )
        return vals_list

    @api.onchange("category_id")
    def _onchange_category_autofill(self) -> None:
        if not self.category_id:
            return

        last_request = self._recent_approved_by_owner(limit=1)

        if not last_request:
            return

        if self.category_id.has_location == "required" and not self.location:
            self.location = last_request.location

        if self.category_id.has_partner == "required" and not self.partner_id:
            self.partner_id = last_request.partner_id

        if self.category_id.has_reference == "required" and not self.reference:
            self.reference = last_request.reference

    def _check_has_document_has_attachment(self) -> None:
        if self.has_document == "required" and not self.count_attachment:
            trace.REFUSAL.event("no_attachment", request=self.id)
            raise UserError(self.env._("You have to attach at least one document."))

        if self.has_document != "required":
            return
        requirements = self.category_id.document_requirement_ids.filtered("required")
        if not requirements:
            return

        satisfied = self.attachment_ids.approval_requirement_id
        missing = requirements - satisfied
        trace.DOCUMENT.event(
            "requirements",
            request=self.id,
            category=self.category_id.id,
            required=requirements.ids,
            satisfied=satisfied.ids,
            missing=missing.ids,
            attachments=self.count_attachment,
        )
        if missing:
            trace.REFUSAL.event(
                "missing_documents",
                request=self.id,
                required=len(requirements),
                missing=missing.ids,
            )
            raise UserError(
                self.env._(
                    "Missing required documents: %(missing)s\n\n"
                    "Attach a file for each, and set its 'Satisfies "
                    "Requirement' so the approvers know which document is "
                    "which.",
                    missing=", ".join(missing.mapped("name")),
                ),
            )

    def _check_category_required_fields(self) -> None:
        field_mapping = self._get_category_required_field_mapping()
        missing_fields = []

        for has_field, (field_name, field_label) in field_mapping.items():
            has_value = getattr(self, has_field, "no")
            if has_value == "required":
                if self._is_required_field_skipped(has_field):
                    continue
                field_value = getattr(self, field_name, None)
                if not field_value:
                    missing_fields.append(field_label)

        if self.has_date_range == "required" and not self.date_end:
            missing_fields.append(self.env._("Period End Date"))

        if missing_fields:
            trace.REFUSAL.event(
                "missing_required_fields",
                request=self.id,
                category=self.category_id.id,
                fields=len(missing_fields),
            )
            raise UserError(
                self.env._(
                    "The following required fields are empty:\n\n%(fields)s\n\n"
                    "Please fill them before submitting the request.",
                    fields="\n".join(f"- {f}" for f in missing_fields),
                ),
            )

    def _is_required_field_skipped(self, has_field: str) -> bool:
        return False

    def _get_category_required_field_mapping(
        self,
    ) -> dict[str, tuple[str, str]]:
        return {
            "has_date": ("date", self.env._("Date")),
            "has_date_deadline": ("date_deadline", self.env._("Deadline")),
            "has_date_planned": ("date_planned", self.env._("Planned Date")),
            "has_date_range": ("date_start", self.env._("Period Start Date")),
            "has_partner": ("partner_id", self.env._("Contact")),
            "has_quantity": ("quantity", self.env._("Quantity")),
            "has_amount": ("amount", self.env._("Amount")),
            "has_reference": ("reference", self.env._("Reference")),
            "has_location": ("location", self.env._("Location")),
        }

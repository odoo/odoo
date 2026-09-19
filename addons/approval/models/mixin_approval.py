from contextlib import contextmanager
from datetime import timedelta
from typing import TYPE_CHECKING, Any

from markupsafe import Markup, escape

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.tools import SQL

from . import approval_trace as trace

if TYPE_CHECKING:
    from odoo.addons.approval.models.approval_category import ApprovalCategory


class MixinApproval(models.AbstractModel):
    _name = "mixin.approval"
    _inherit = ["mixin.approval.source"]
    _description = "Approval Mixin for Source Documents"

    approval_request_id = fields.Many2one(
        comodel_name="approval.request",
        index=True,
        copy=False,
        readonly=True,
        tracking=True,
        help="Link to the approval request for this document. Automatically created when approval is requested.",
    )
    approval_state = fields.Selection(
        related="approval_request_id.state",
        string="Approval Status",
        help="""Current approval status:
        • new: Approval created but not submitted
        • pending: Waiting for approvers
        • approved: All required approvals obtained
        • refused: Approval was refused (terminal)
        • cancelled: Approval was retracted or expired (terminal)""",
    )
    date_approval_granted = fields.Datetime(
        related="approval_request_id.date_approval_granted",
        string="Approval Granted Date",
        copy=False,
        readonly=True,
        tracking=True,
        help="Date and time when final approval was granted",
    )
    approval_progress = fields.Float(
        related="approval_request_id.approval_progress",
        help="Percentage of approvals completed (approved / total approvers)",
    )
    pending_approver_ids = fields.Many2many(
        related="approval_request_id.pending_approver_ids",
        string="Pending Approvers",
        help="Users who still need to approve this document",
    )
    date_approval_requested = fields.Datetime(
        related="approval_request_id.date_confirmed",
        string="Approval Requested Date",
        copy=False,
        readonly=True,
        tracking=True,
        help="Date and time when approval was requested for this document",
    )
    approval_user_ids = fields.Many2many(
        related="approval_request_id.user_ids",
        string="Approvers",
        help="Users who need to approve this document",
    )
    approval_required = fields.Boolean(
        compute="_compute_approval_required",
        store=False,
        help="Whether this document requires approval based on current rules",
    )
    can_request_approval = fields.Boolean(
        compute="_compute_can_request_approval",
        help="Whether approval can be requested (all required fields filled)",
    )

    @api.depends_context("uid", "company")
    def _compute_approval_required(self) -> None:
        cache: dict[tuple, bool] = {}
        hits = 0
        required = 0
        for record in self:
            company_id = False
            if "company_id" in record._fields:
                company_id = record.company_id.id if record.company_id else False
            key = (repr(record._get_domain_approval_category()), company_id)
            if key in cache:
                hits += 1
            else:
                cache[key] = bool(record._find_approval_category())
            record.approval_required = cache[key]
            required += bool(cache[key])
        trace.MIXIN.event(
            "approval_required",
            record=self,
            n=len(self),
            searches=len(cache),
            hits=hits,
            required=required,
        )

    @api.depends("approval_request_id", "approval_required")
    def _compute_can_request_approval(self) -> None:
        for record in self:
            if record.approval_request_id or not record.approval_required:
                record.can_request_approval = False
                continue

            missing_fields = [
                f for f in record._get_fields_approval_required() if not record[f]
            ]
            record.can_request_approval = not missing_fields
            if missing_fields:
                trace.MIXIN.event(
                    "cannot_request_approval",
                    record=record,
                    missing=missing_fields,
                )

    def _check_can_request_approval(self) -> None:
        self.check_singleton()
        if self.approval_request_id:
            trace.REFUSAL.event(
                "request_already_exists",
                record=self,
                request=self.approval_request_id.id,
            )
            raise UserError(
                self.env._("An approval request already exists for this document."),
            )

        missing_fields = [
            f for f in self._get_fields_approval_required() if not self[f]
        ]
        if missing_fields:
            field_names = ", ".join(
                [self._fields[f].string for f in missing_fields if f in self._fields],
            )
            trace.REFUSAL.event(
                "required_fields_empty", record=self, fields=missing_fields
            )
            raise UserError(
                self.env._(
                    "Please fill in the following required fields before requesting approval: %s",
                    field_names,
                ),
            )

        if not self._get_approval_category():
            trace.REFUSAL.event("no_category_for_document", record=self)
            raise UserError(
                self.env._(
                    "No approval category found for this document type. "
                    "Please configure approval categories first.\n\n"
                    "Go to: Approvals → Configuration → Approval Types",
                ),
            )

        if not self.can_request_approval:
            trace.REFUSAL.event(
                "cannot_request_approval",
                record=self,
                required=self._get_fields_approval_required(),
            )
            raise UserError(
                self.env._(
                    "Approval cannot be requested for this document right now.",
                ),
            )

    def action_refuse_approval(self) -> None:
        self.check_singleton()
        self.check_access("write")
        if self.approval_request_id and self.approval_request_id._refuse_cascade():
            self.message_post(
                body=self.env._("Approval request refused (parent document cancelled)"),
                message_type="notification",
            )

    def action_create_approval_request(self) -> dict[str, Any]:
        self.check_singleton()

        self.env.cr.execute(
            SQL(
                "SELECT id FROM %s WHERE id = %s FOR UPDATE",
                SQL.identifier(self._table),
                self.id,
            )
        )
        self.invalidate_recordset(["approval_request_id"])

        self._check_can_request_approval()

        category = self._get_approval_category()
        if not category:
            trace.REFUSAL.event("no_category_at_submit", record=self)
            raise UserError(
                self.env._(
                    "No approval category found for this document type. "
                    "Please configure approval categories first.\n\n"
                    "Go to: Approvals → Configuration → Approval Types",
                ),
            )

        vals = self._prepare_approval_request_values(category)
        approval = self.env["approval.request"].create(vals)
        trace.MIXIN.note(
            "request_raised",
            record=self,
            category=category.id,
            request=approval.id,
        )
        self.write({"approval_request_id": approval.id})

        self._before_approval_request_submit(approval)

        approval.action_confirm()

        self.message_post(
            body=Markup(
                "<a href='#' data-oe-model='approval.request' data-oe-id='%s'>%s</a> %s"
            )
            % (approval.id, escape(approval.name), self.env._("created")),
            message_type="notification",
        )

        return self._get_approval_submitted_action(approval)

    def _before_approval_request_submit(self, approval) -> None:
        pass

    def _get_approval_submitted_action(self, approval) -> dict[str, Any]:
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "success",
                "title": self.env._("Approval Requested"),
                "message": self.env._(
                    "Approval request '%s' has been created and submitted.",
                    approval.name,
                ),
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }

    def _approval_rate_limit_rate_date(self):
        self.check_singleton()
        return fields.Date.context_today(self)

    def _approval_rate_limit_exceeded(
        self,
        *,
        hours: int,
        max_count: int,
        max_amount: float,
        under_threshold_amount: float,
        excluded_states: tuple = ("cancel",),
    ) -> bool:
        self.check_singleton()
        company = self.company_id
        company_currency = company.currency_id
        rate_date = self._approval_rate_limit_rate_date()

        policed_user = self.create_uid or self.env.user
        window = Domain(
            [
                ("company_id", "=", company.id),
                ("create_uid", "=", policed_user.id),
                ("create_date", ">=", fields.Datetime.now() - timedelta(hours=hours)),
                ("state", "not in", list(excluded_states)),
            ],
        )
        if self.id:
            window &= Domain([("id", "!=", self.id)])

        currencies = self.env["res.currency"].browse(
            [
                currency.id
                for (currency,) in self.sudo()._read_group(window, ["currency_id"], [])
                if currency
            ],
        )

        count = 0
        cumulative = 0.0
        if currencies:
            under_threshold = Domain.FALSE
            for currency in currencies:
                under_threshold |= Domain(
                    [
                        ("currency_id", "=", currency.id),
                        (
                            "amount_total",
                            "<",
                            company_currency._convert(
                                under_threshold_amount, currency, company, rate_date
                            ),
                        ),
                    ],
                )
            for currency, group_count, group_total in self.sudo()._read_group(
                window & under_threshold,
                ["currency_id"],
                ["__count", "amount_total:sum"],
            ):
                count += group_count
                cumulative += currency._convert(
                    group_total or 0.0, company_currency, company, rate_date
                )

        if count >= max_count:
            trace.MIXIN.note(
                "rate_limit_count",
                record=self,
                user=policed_user.id,
                hours=hours,
                count=count,
                max_count=max_count,
            )
            return True

        own_amount = self.currency_id._convert(
            self.amount_total, company_currency, company, rate_date
        )
        exceeded = cumulative + own_amount >= max_amount
        trace.MIXIN.event(
            "rate_limit_amount",
            record=self,
            user=policed_user.id,
            hours=hours,
            count=count,
            cumulative=cumulative,
            own=own_amount,
            max_amount=max_amount,
            exceeded=exceeded,
        )
        return exceeded

    def _get_fields_approval_protected(self) -> list[str]:
        return []

    _APPROVAL_OUTPUT_FIELDS = frozenset(
        {"approval_state", "date_approval_granted", "date_approval_requested"}
    )

    @api.model_create_multi
    def create(self, vals_list: list[dict[str, Any]]):
        for vals in vals_list:
            self._check_no_forged_approval_outputs(vals)
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list, strict=True):
            if vals.get("approval_request_id"):
                record._check_approval_request_link(vals["approval_request_id"])
        return records

    def _check_no_forged_approval_outputs(self, vals: dict[str, Any]) -> None:
        """What a document says about its approval is read from its request.

        These columns are stored copies of the request, kept for search and
        domains. Writing one does not reach the request: it makes the document
        claim a decision nobody took, and every gate that reads the document
        believes it. Nothing legitimate writes them -- the ORM updates a stored
        related field without calling `write` -- so the refusal holds for the
        superuser too.
        """
        forged = self._APPROVAL_OUTPUT_FIELDS & vals.keys()
        if forged:
            trace.REFUSAL.event(
                "approval_output_written", records=self, fields=sorted(forged)
            )
            raise ValidationError(
                self.env._(
                    "%(fields)s cannot be written: a document's approval status "
                    "is its approval request's, and changes only through a "
                    "decision on that request.",
                    fields=", ".join(sorted(forged)),
                )
            )

    def _check_approval_request_link(self, request_id: int | Any) -> None:
        """A document may point only at an approval request it answers to.

        Three relations are real. The request is about this record: the
        engine's own link. The request produced this record: its category's
        `target_model` is this model, and the link is written inside the
        request's `_link_produced_documents` (or `_producing_documents`) window,
        which only server code opens. A bill or an order created from an
        approved request is covered by it; one a user points at that request is
        not. Or the request has no subject and nobody has decided it yet: it is
        bound to the record here, so it cannot be adopted twice. Anything else
        would lend the record a decision taken about something else.
        """
        request = (
            self.env["approval.request"]
            .sudo()
            .browse(request_id.id if hasattr(request_id, "id") else request_id)
        )
        for record in self:
            if request.res_model == record._name and request.res_id == record.id:
                continue
            if (
                request.target_model
                and request.target_model == record._name
                and request._is_producing_documents()
            ):
                continue
            if not request.res_model and not request.res_id and request.state == "new":
                request.write({"res_model": record._name, "res_id": record.id})
                continue
            trace.REFUSAL.event(
                "approval_request_link_foreign",
                record=record,
                request=request.id,
                request_subject=f"{request.res_model},{request.res_id}",
                request_state=request.state,
            )
            raise ValidationError(
                self.env._(
                    "%(document)s cannot be linked to approval request "
                    "%(request)s: that request is about another record, or was "
                    "already decided without one.",
                    document=record.display_name,
                    request=request.display_name,
                )
            )

    def write(self, vals: dict[str, Any]) -> bool:
        self._check_no_forged_approval_outputs(vals)
        if vals.get("approval_request_id"):
            if len(self) > 1:
                trace.REFUSAL.event(
                    "approval_request_link_many", records=self, count=len(self)
                )
                raise ValidationError(
                    self.env._(
                        "One approval request is about one record; it cannot be "
                        "linked to %(count)s at once.",
                        count=len(self),
                    )
                )
            request_id = vals["approval_request_id"]
            request_id = request_id.id if hasattr(request_id, "id") else request_id
            self.filtered(
                lambda record: record.approval_request_id.id != request_id
            )._check_approval_request_link(request_id)
        if not self.env.su:
            protected = set(self._get_fields_approval_protected())
            touched = protected & vals.keys()
            if touched:
                blocked = self.filtered(lambda r: r.approval_state == "pending")
                if blocked:
                    trace.REFUSAL.event(
                        "protected_while_pending",
                        records=blocked,
                        fields=sorted(touched),
                    )
                    raise UserError(
                        self.env._(
                            "Cannot modify %(fields)s while approval is "
                            "pending — approvers are deciding on the current "
                            "values. Withdraw or refuse the approval first.\n\n"
                            "Document: %(name)s",
                            fields=", ".join(sorted(touched)),
                            name=blocked[:1].display_name,
                        ),
                    )
        invalidated = self._get_records_approval_invalidated_by(vals)
        for record, _fields_changed in invalidated:
            # Refuse the edit rather than leave an approval standing that no
            # longer describes the document, where the request cannot be reset.
            record.approval_request_id.sudo()._check_reset_allowed()
        result = super().write(vals)
        for record, fields_changed in invalidated:
            record._reset_approval_for_subject_change(fields_changed)
        return result

    def _is_approval_invalidated_by_changes(self, fields_changed: list[str]) -> bool:
        """Whether changing these protected fields after approval takes the
        approval away. A document that re-checks some of them against what was
        approved at its own gate -- an amount compared at posting -- may keep
        the approval for those, and only those."""
        return True

    def _get_records_approval_invalidated_by(self, vals: dict[str, Any]):
        """The approved records this write would change in what was approved.

        Compared value by value, not by key: a form saves the fields it shows,
        and an unchanged partner written back must not take an approval away.
        """
        protected = set(self._get_fields_approval_protected()) & vals.keys()
        if not protected or self.env.context.get("approval_keep_on_subject_change"):
            return []
        invalidated = []
        for record in self:
            if record.approval_state != "approved":
                continue
            changed = sorted(
                name
                for name in protected
                if record._approval_value_changes(name, vals[name])
            )
            if changed and record._is_approval_invalidated_by_changes(changed):
                invalidated.append((record, changed))
        trace.MIXIN.event(
            "subject_change_check",
            records=self,
            fields=sorted(protected),
            invalidated=[record.id for record, _changed in invalidated],
        )
        return invalidated

    def _approval_value_changes(self, name: str, value: Any) -> bool:
        self.check_singleton()
        field = self._fields[name]
        current = self[name]
        if field.type in ("one2many", "many2many"):
            ids = set(current.ids)
            for command in value or ():
                if not isinstance(command, (list, tuple)):
                    return True
                code = command[0]
                if code in (Command.CREATE, Command.UPDATE):
                    return True
                if code in (Command.DELETE, Command.UNLINK) and command[1] in ids:
                    return True
                if code == Command.LINK and command[1] not in ids:
                    return True
                if code == Command.CLEAR and ids:
                    return True
                if code == Command.SET and set(command[2]) != ids:
                    return True
            return False
        if field.type == "many2one":
            new_id = (
                value.id if isinstance(value, models.BaseModel) else (value or False)
            )
            return new_id != current.id
        return (
            field.convert_to_record(field.convert_to_cache(value, self), self)
            != current
        )

    def _reset_approval_for_subject_change(self, fields_changed: list[str]) -> None:
        """What was approved is not what the document says any more: the approval
        goes back to draft, recorded as a reset with the fields that moved, and
        the document hears it as it would from a manager's reset."""
        self.check_singleton()
        labels = ", ".join(self._fields[name].string for name in fields_changed)
        trace.MIXIN.note(
            "approval_reset_by_subject_change",
            record=self,
            request=self.approval_request_id.id,
            fields=fields_changed,
        )
        self.approval_request_id.sudo()._force_draft(
            note=self.env._(
                "The approved document changed (%(fields)s) by %(user)s, so the "
                "approval no longer covers it.",
                fields=labels,
                user=self.env.user.name,
            )
        )

    @api.ondelete(at_uninstall=False)
    def _unlink_except_pending_approval(self) -> None:
        for record in self:
            if record.approval_state == "pending":
                trace.REFUSAL.event(
                    "unlink_with_pending_approval",
                    record=record,
                    request=record.approval_request_id.id,
                )
                raise UserError(
                    self.env._(
                        "Cannot delete %(name)s: it has a pending approval "
                        "request (%(request)s). Cancel or refuse the "
                        "approval first.",
                        name=record.display_name,
                        request=record.approval_request_id.display_name,
                    ),
                )

    def unlink(self) -> bool:
        draft_requests = self.env["approval.request"]
        for record in self:
            if record.approval_request_id and record.approval_state == "new":
                draft_requests |= record.approval_request_id
        res = super().unlink()
        if draft_requests:
            draft_requests.sudo().unlink()
        return res

    def action_view_approval_request(self) -> dict[str, Any]:
        self.check_singleton()
        return self._get_approval_request_view_action()

    def _clear_refused_approval_link(self) -> None:
        for record in self:
            if record.approval_request_id and record.approval_state in (
                "refused",
                "cancelled",
            ):
                approval_name = record.approval_request_id.name
                trace.MIXIN.note(
                    "link_cleared",
                    record=record,
                    request=record.approval_request_id.id,
                    state=record.approval_state,
                )
                record.approval_request_id = False
                record.message_post(
                    body=record.env._(
                        "Approval link cleared (previous approval: %s). "
                        "A new approval can be requested when confirming.",
                        approval_name,
                    ),
                    message_type="notification",
                )

    def _get_domain_approval_category(self) -> list[Any]:
        return []

    def _get_candidate_approval_categories(self) -> "ApprovalCategory":  # noqa: UP037 — ORM methods are runtime-introspected (api_doc, /json/2); the TYPE_CHECKING import means the class isn't in the runtime namespace, so the annotation must stay quoted.
        self.check_singleton()
        domain = self._get_domain_approval_category()
        if not domain:
            return self.env["approval.category"]

        company_id = False
        if "company_id" in self._fields:
            company_id = self.company_id.id if self.company_id else False

        return self.env["approval.category"].search(
            domain + [("company_id", "in", (company_id, False))],
        )

    def _find_approval_category(self) -> "ApprovalCategory":  # noqa: UP037 — see _get_candidate_approval_categories.
        self.check_singleton()
        categories = self._get_candidate_approval_categories()
        for category in categories:
            if category._is_applicable_for(self):
                trace.MIXIN.event(
                    "category_matched",
                    record=self,
                    category=category.id,
                    candidates=categories.ids,
                )
                return category
        trace.MIXIN.event(
            "category_unmatched",
            record=self,
            candidates=categories.ids,
        )
        return self._get_approval_category_fallback(categories)

    def _get_approval_category(self) -> "ApprovalCategory | bool":  # noqa: UP037 — see _get_candidate_approval_categories.
        self.check_singleton()
        if not self._get_domain_approval_category():
            trace.MIXIN.event("approval_category", record=self, outcome="no_domain")
            return False
        categories = self._get_candidate_approval_categories()
        if not categories:
            trace.MIXIN.event(
                "approval_category", record=self, outcome="none_configured"
            )
            self._raise_approval_category_not_configured()
            return False
        category = self._find_approval_category()
        if category:
            trace.MIXIN.event(
                "approval_category",
                record=self,
                outcome="matched",
                category=category.id,
                candidates=len(categories),
            )
            return category
        trace.MIXIN.event(
            "approval_category",
            record=self,
            outcome="no_match",
            candidates=categories.ids,
        )
        self._raise_approval_category_not_matched(categories)
        return False

    def _get_approval_category_fallback(self, categories):
        self.check_singleton()
        trace.DEGRADED.event(
            "no_category_fallback", record=self, candidates=len(categories)
        )
        return self.env["approval.category"].browse()

    def _raise_approval_category_not_configured(self) -> None:
        trace.DEGRADED.event("category_not_configured_unraised", record=self)

    def _raise_approval_category_not_matched(self, categories) -> None:
        trace.DEGRADED.event(
            "category_not_matched_unraised", record=self, candidates=categories.ids
        )

    def _get_approval_reason_html(self) -> str:
        self.check_singleton()
        return self.env._("Approval requested for %s", self.display_name)

    def _get_approval_request_name(self) -> str:
        return self.env._("Approval for %s", self.display_name)

    def _get_approval_request_view_action(self) -> dict[str, Any]:
        self.check_singleton()
        return {
            "name": self.env._("Approval Request"),
            "type": "ir.actions.act_window",
            "res_model": "approval.request",
            "res_id": self.approval_request_id.id,
            "view_mode": "form",
            "target": "current",
        }

    def _get_fields_approval_required(self) -> list[str]:
        return []

    def _prepare_approval_request_values(self, category: Any) -> dict[str, Any]:
        company_id = False
        if "company_id" in self._fields:
            company_id = self.company_id.id if self.company_id else False

        vals = {
            "category_id": category.id,
            "request_owner_id": self.env.user.id,
            "company_id": company_id or self.env.company.id,
            "res_model": self._name,
            "res_id": self.id,
            "reason": self._get_approval_reason_html(),
        }

        field_mapping = {
            "partner_id": "partner_id",
            "amount_total": "amount",
            "date_order": "date",
            "currency_id": "currency_id",
        }

        for source_field, target_field in field_mapping.items():
            if source_field in self._fields and self[source_field]:
                value = self[source_field]
                if hasattr(value, "id"):
                    vals[target_field] = value.id
                else:
                    vals[target_field] = value

        # Keyed to this record: a document created further down the same call
        # chain must not inherit the binding link from the context.
        binding_for = self.env.context.get("approval_binding_for")
        if binding_for and tuple(binding_for[:2]) == (self._name, self.id):
            vals["binding_id"] = binding_for[2]

        trace.MIXIN.event(
            "request_values",
            record=self,
            category=category.id,
            fields=sorted(vals),
            binding=vals.get("binding_id"),
        )
        return vals

    def _on_approval_state_changed(self, new_state: str) -> None:
        trace.MIXIN.note(
            "told_state",
            record=self,
            state=new_state,
            request=self.approval_request_id.id,
        )
        if new_state == "approved":
            self._on_approval_approved()
        elif new_state == "refused":
            self._on_approval_refused()
        elif new_state == "cancelled":
            self._on_approval_cancelled()
        elif new_state == "pending":
            self._on_approval_revoked()
        elif new_state == "new":
            self._on_approval_reset()

    def _approval_decider_names(self, state: str = "approved") -> str:
        self.check_singleton()
        deciders = self.approval_request_id.approver_ids.filtered(
            lambda approver: approver.state == state and approver.decision_date,
        )
        trace.MIXIN.event(
            "decider_names",
            record=self,
            state=state,
            rows=self.approval_request_id.approver_ids.ids,
            deciders=deciders.ids,
        )
        return ", ".join(
            (approver.decided_by_user_id or approver.user_id).name
            for approver in deciders
        )

    @contextmanager
    def _approval_side_effect(self, failure_note: str):
        self.check_singleton()
        try:
            with self.env.cr.savepoint():
                yield
        except (UserError, ValidationError) as error:
            trace.MIXIN.note(
                "side_effect_failed",
                record=self,
                error=type(error).__name__,
            )
            self.message_post(
                body=failure_note % {"error": str(error)},
                message_type="notification",
            )

    def _on_approval_progress(self) -> None:
        """A decision met a step of this document's request, which is still pending."""
        self.check_singleton()

    def _on_approval_approved(self) -> None:
        self.check_singleton()
        self.message_post(
            body=self.env._("Approval granted"),
            message_type="notification",
        )

    def _on_approval_refused(self) -> None:
        self.check_singleton()
        self.message_post(
            body=self.env._("Approval refused"),
            message_type="notification",
        )

    def _on_approval_cancelled(self) -> None:
        self.check_singleton()
        self.message_post(
            body=self.env._(
                "Approval cancelled (retracted or expired — not a refusal)."
            ),
            message_type="notification",
        )

    def _on_approval_revoked(self) -> None:
        self.check_singleton()
        self.message_post(
            body=self.env._(
                "An approver withdrew their approval — the approval "
                "is pending again. Review this document before "
                "processing it further.",
            ),
            message_type="notification",
        )
        if "activity_ids" in self._fields:
            responsible = getattr(self, "user_id", None) or self.create_uid
            trace.MIXIN.note(
                "withdrawal_todo",
                record=self,
                responsible=responsible.id,
                request=self.approval_request_id.id,
            )
            self.activity_schedule(
                "mail.mail_activity_data_todo",
                user_id=responsible.id,
                summary=self.env._("Approval was withdrawn"),
                note=self.env._(
                    "The approval linked to this document returned to "
                    "pending after a withdrawal. Confirm whether the "
                    "document should proceed.",
                ),
            )

    def _on_approval_reset(self) -> None:
        self.check_singleton()
        trace.MIXIN.event(
            "reset_notice",
            record=self,
            reset_from=self.env.context.get("approval_reset_from"),
        )
        if self.env.context.get("approval_reset_from") == "approved":
            body = self.env._(
                "The approval linked to this document was reset to draft — "
                "the prior approval is no longer valid. Review this document "
                "before processing it further.",
            )
        else:
            body = self.env._(
                "The approval request linked to this document was reset to draft "
                "and can be submitted again.",
            )
        self.message_post(body=body, message_type="notification")

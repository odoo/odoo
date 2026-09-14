from odoo import api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def default_get(self, fields):
        self_ctx = self
        if self.env.context.get("default_applicant_id"):
            self_ctx = self.with_context(
                default_res_model="hr.applicant",
                default_res_model_id=self.env.ref(
                    "hr_recruitment.model_hr_applicant"
                ).id,
                default_res_id=self.env.context.get("default_applicant_id"),
                default_partner_ids=self.env.context.get("default_partner_ids"),
                default_name=self.env.context.get("default_name"),
            )

        defaults = super(CalendarEvent, self_ctx).default_get(fields)

        if "applicant_id" not in defaults:
            res_model = defaults.get("res_model", False) or self_ctx.env.context.get(
                "default_res_model"
            )
            res_model_id = defaults.get(
                "res_model_id", False
            ) or self_ctx.env.context.get("default_res_model_id")
            if (res_model and res_model == "hr.applicant") or (
                res_model_id
                and self_ctx.env["ir.model"].sudo().browse(res_model_id).model
                == "hr.applicant"
            ):
                defaults["applicant_id"] = defaults.get(
                    "res_id", False
                ) or self_ctx.env.context.get("default_res_id", False)

        return defaults

    applicant_id = fields.Many2one(
        comodel_name="hr.applicant",
        index="btree_not_null",
        ondelete="set null",
    )

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        if not self.env["hr.applicant"].has_access("read"):
            return events
        # Keyed on the event's own applicant, not on a context key: a meeting
        # created from the Calendar app with an applicant on it used to get no
        # CV while the same meeting created from the applicant's own button did.
        # Occurrences are excluded -- `_apply_recurrence` copies the base event's
        # values, applicant included, so keying on the record alone would put a
        # copy of every CV on every occurrence. `recurrence_id` alone does not
        # tell them apart: the base event carries it too by the time `create`
        # returns, so the base is the one the recurrence points back at.
        scheduled = events.filtered(
            lambda event: (
                event.applicant_id
                and (
                    not event.recurrence_id
                    or event.recurrence_id.base_event_id == event
                )
            )
        )
        if not scheduled:
            return events
        copies = [
            {
                "name": attachment.name,
                "type": "binary",
                "datas": attachment.datas,
                "res_model": event._name,
                "res_id": event.id,
            }
            for applicant, applicant_events in scheduled.grouped("applicant_id").items()
            for attachment in applicant.attachment_ids
            for event in applicant_events
        ]
        if copies:
            _debug.lifecycle(
                "applicant_documents_copied",
                events=len(scheduled),
                attachments=len(copies),
            )
            self.env["ir.attachment"].create(copies)
        return events

    def _compute_is_highlighted(self):
        super()._compute_is_highlighted()
        applicant_id = self.env.context.get("active_id")
        if self.env.context.get("active_model") == "hr.applicant" and applicant_id:
            for event in self:
                if event.applicant_id.id == applicant_id:
                    event.is_highlighted = True

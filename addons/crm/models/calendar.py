from odoo import api, fields, models


class CalendarEvent(models.Model):
    _inherit = "calendar.event"

    @api.model
    def default_get(self, fields):
        if self.env.context.get("default_opportunity_id"):
            self = self.with_context(
                default_res_model_id=self.env.ref("crm.model_crm_lead").id,
                default_res_id=self.env.context["default_opportunity_id"],
            )
        defaults = super().default_get(fields)

        if "opportunity_id" not in defaults:
            if self._is_crm_lead(defaults, self.env.context):
                defaults["opportunity_id"] = defaults.get(
                    "res_id", False
                ) or self.env.context.get("default_res_id", False)

        return defaults

    opportunity_id = fields.Many2one(
        comodel_name="crm.lead",
        index=True,
        domain="[('type', '=', 'opportunity')]",
        ondelete="set null",
    )

    def _compute_is_highlighted(self):
        super()._compute_is_highlighted()
        if self.env.context.get("active_model") == "crm.lead":
            opportunity_id = self.env.context.get("active_id")
            for event in self:
                if event.opportunity_id.id == opportunity_id:
                    event.is_highlighted = True

    @api.model_create_multi
    def create(self, vals_list):
        events = super().create(vals_list)
        for event in events:
            if event.opportunity_id and not event.activity_ids:
                event.opportunity_id.log_meeting(event)
        return events

    def _is_crm_lead(self, defaults, ctx=None):
        res_model = defaults.get("res_model", False) or (
            ctx and ctx.get("default_res_model")
        )
        res_model_id = defaults.get("res_model_id", False) or (
            ctx and ctx.get("default_res_model_id")
        )

        return (res_model and res_model == "crm.lead") or (
            res_model_id
            and self.env["ir.model"].sudo().browse(res_model_id).model == "crm.lead"
        )

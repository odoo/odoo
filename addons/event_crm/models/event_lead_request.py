from odoo import api, fields, models, modules


class EventLeadRequest(models.Model):
    _name = "event.lead.request"
    _description = "Event Lead Request"
    _log_access = False
    _rec_name = "event_id"
    _order = "id asc"

    _REGISTRATIONS_BATCH_SIZE = 200

    event_id = fields.Many2one(
        comodel_name="event.event",
        required=True,
        ondelete="cascade",
    )
    event_lead_rule_ids = fields.Many2many(
        comodel_name="event.lead.rule",
        string="Lead Rules",
    )
    processed_registration_id = fields.Integer(
        help="The ID of the last processed event.registration, used to know where to resume."
    )

    _uniq_event = models.Constraint(
        "unique(event_id)",
        "You can only have one generation request per event at a time.",
    )

    @api.model
    def _cron_generate_leads(self, job_limit=100, registrations_batch_size=None):
        auto_commit = not modules.module.current_test

        registrations_batch_size = (
            registrations_batch_size or self._REGISTRATIONS_BATCH_SIZE
        )
        generate_requests = self.env["event.lead.request"].search([], limit=job_limit)
        fulfilled_requests = self.env["event.lead.request"]
        for generate_request in generate_requests:
            registrations_to_process = self.env["event.registration"].search(  # noqa: E8507 - one batch of registrations per request
                [
                    ("event_id", "=", generate_request.event_id.id),
                    ("state", "not in", ["draft", "cancel"]),
                    ("id", ">", generate_request.processed_registration_id),
                ],
                limit=registrations_batch_size,
                order="id asc",
            )

            registrations_to_process._apply_lead_generation_rules(
                event_lead_rules=generate_request.event_lead_rule_ids
            )

            if len(registrations_to_process) < registrations_batch_size:
                fulfilled_requests += generate_request
            else:
                generate_request.processed_registration_id = registrations_to_process[
                    -1
                ].id

            if auto_commit:
                self.env.cr.commit()

        if generate_requests - fulfilled_requests:
            self.env.ref("event_crm.ir_cron_generate_leads")._trigger()

        if fulfilled_requests:
            fulfilled_requests.unlink()

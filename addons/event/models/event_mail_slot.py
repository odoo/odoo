from odoo import api, fields, models


class EventMailSlot(models.Model):
    _name = "event.mail.slot"
    _description = "Slot Mail Scheduler"
    _rec_name = "scheduler_id"
    _order = "scheduled_date DESC, id ASC"

    event_slot_id = fields.Many2one(
        comodel_name="event.slot",
        string="Slot",
        required=True,
        ondelete="cascade",
    )
    scheduled_date = fields.Datetime(
        string="Schedule Date",
        compute="_compute_scheduled_date",
        store=True,
    )
    scheduler_id = fields.Many2one(
        comodel_name="event.mail",
        string="Mail Scheduler",
        index=True,
        required=True,
        ondelete="cascade",
    )
    # contact and status
    last_registration_id = fields.Many2one(
        comodel_name="event.registration",
        string="Last Attendee",
    )
    mail_count_done = fields.Integer(
        string="# Sent",
        copy=False,
        readonly=True,
    )
    mail_done = fields.Boolean(
        string="Sent",
        copy=False,
        readonly=True,
    )

    @api.depends(
        "event_slot_id.start_datetime",
        "event_slot_id.end_datetime",
        "scheduler_id.interval_unit",
        "scheduler_id.interval_type",
    )
    def _compute_scheduled_date(self):
        for mail_slot in self:
            scheduler = mail_slot.scheduler_id
            if scheduler.interval_type in ("before_event", "after_event_start"):
                date, sign = (
                    mail_slot.event_slot_id.start_datetime,
                    (scheduler.interval_type == "before_event" and -1) or 1,
                )
            else:
                date, sign = (
                    mail_slot.event_slot_id.end_datetime,
                    (scheduler.interval_type == "after_event" and 1) or -1,
                )
            mail_slot.scheduled_date = (
                date.replace(microsecond=0)
                + scheduler._get_schedule_delta(sign * scheduler.interval_nbr)
                if date
                else False
            )

        next_schedule = self.filtered("scheduled_date").mapped("scheduled_date")
        if next_schedule and (
            cron := self.env.ref("event.event_mail_scheduler", raise_if_not_found=False)
        ):
            cron._trigger(next_schedule)

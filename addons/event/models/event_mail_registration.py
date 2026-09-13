import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class EventMailRegistration(models.Model):
    _name = "event.mail.registration"
    _description = "Registration Mail Scheduler"
    _rec_name = "scheduler_id"
    _order = "scheduled_date DESC, id ASC"

    scheduler_id = fields.Many2one(
        comodel_name="event.mail",
        string="Mail Scheduler",
        index=True,
        required=True,
        ondelete="cascade",
    )
    registration_id = fields.Many2one(
        comodel_name="event.registration",
        string="Attendee",
        index=True,
        required=True,
        ondelete="cascade",
    )
    scheduled_date = fields.Datetime(
        string="Scheduled Time",
        compute="_compute_scheduled_date",
        store=True,
    )
    mail_sent = fields.Boolean()

    _scheduler_registration_uniq = models.Constraint(
        "unique(scheduler_id, registration_id)",
        "A registration can only be scheduled once per communication.",
    )

    @api.depends(
        "registration_id", "scheduler_id.interval_unit", "scheduler_id.interval_type"
    )
    def _compute_scheduled_date(self):
        for mail in self:
            if mail.registration_id:
                mail.scheduled_date = mail.registration_id.create_date.replace(
                    microsecond=0
                ) + mail.scheduler_id._get_schedule_delta(
                    mail.scheduler_id.interval_nbr
                )
            else:
                mail.scheduled_date = False

    def execute(self):
        # Deprecated, to be called only from parent scheduler
        skip_domain = self._get_domain_skip() + [
            ("registration_id.state", "in", ("open", "done"))
        ]
        self.filtered_domain(skip_domain)._execute_on_registrations()

    def _execute_on_registrations(self):
        """Private mail registration execution. We consider input is already
        filtered at this point, allowing to let caller do optimizations when
        managing batches of registrations."""
        todo = self.filtered(lambda r: r.scheduler_id.notification_type == "mail")
        for scheduler, reg_mails in todo.grouped("scheduler_id").items():
            # exclusion_list should not be applied as registering to an event is implicitly
            # subscribing to the emails relevant to the event such as the email containing the ticket
            scheduler.with_context(default_use_exclusion_list=False)._send_mail(
                reg_mails.registration_id
            )
        todo.mail_sent = True
        return todo

    def _get_domain_skip(self):
        """Domain of mail registrations ot skip: not already done, linked to
        a valid registration, and scheduled in the past."""
        return [
            ("mail_sent", "=", False),
            ("scheduled_date", "!=", False),
            ("scheduled_date", "<=", self.env.cr.now()),
        ]

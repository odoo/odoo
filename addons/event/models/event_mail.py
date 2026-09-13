import logging
from itertools import batched

from dateutil.relativedelta import relativedelta
from markupsafe import Markup

from odoo import api, fields, models, modules
from odoo.tools.rendering_tools import QWebError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class EventMail(models.Model):
    """Automated mailing scheduled on an event."""

    _name = "event.mail"
    _inherit = ["mixin.event.mail.schedule"]
    _rec_name = "event_id"
    _description = "Event Automated Mailing"

    event_id = fields.Many2one(
        comodel_name="event.event",
        index=True,
        required=True,
        ondelete="cascade",
    )
    sequence = fields.Integer(string="Display order")
    scheduled_date = fields.Datetime(
        string="Schedule Date",
        compute="_compute_scheduled_date",
        store=True,
    )
    error_datetime = fields.Datetime(string="Last Error")
    # contact and status
    last_registration_id = fields.Many2one(
        comodel_name="event.registration",
        string="Last Attendee",
    )
    mail_registration_ids = fields.One2many(
        comodel_name="event.mail.registration",
        inverse_name="scheduler_id",
        help="Communication related to event registrations",
    )
    mail_slot_ids = fields.One2many(
        comodel_name="event.mail.slot",
        inverse_name="scheduler_id",
        help="Slot-based communication",
    )
    mail_done = fields.Boolean(
        string="Sent",
        copy=False,
        readonly=True,
    )
    mail_state = fields.Selection(
        selection=[
            ("running", "Running"),
            ("scheduled", "Scheduled"),
            ("sent", "Sent"),
            ("error", "Error"),
            ("cancelled", "Cancelled"),
        ],
        string="Global communication Status",
        compute="_compute_mail_state",
    )
    mail_count_done = fields.Integer(
        string="# Sent",
        copy=False,
        readonly=True,
    )

    @api.depends(
        "event_id.date_begin",
        "event_id.date_end",
        "interval_type",
        "interval_unit",
        "interval_nbr",
    )
    def _compute_scheduled_date(self):
        for scheduler in self:
            if scheduler.interval_type == "after_sub":
                date, sign = scheduler.event_id.create_date, 1
            elif scheduler.interval_type in ("before_event", "after_event_start"):
                date, sign = (
                    scheduler.event_id.date_begin,
                    (scheduler.interval_type == "before_event" and -1) or 1,
                )
            else:
                date, sign = (
                    scheduler.event_id.date_end,
                    (scheduler.interval_type == "after_event" and 1) or -1,
                )

            scheduler.scheduled_date = (
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

    @api.depends("error_datetime", "interval_type", "mail_done", "event_id")
    def _compute_mail_state(self):
        for scheduler in self:
            # issue detected
            if scheduler.error_datetime:
                scheduler.mail_state = "error"
            # event cancelled
            elif (
                not scheduler.mail_done and scheduler.event_id.kanban_state == "cancel"
            ):
                scheduler.mail_state = "cancelled"
            # registrations based
            elif scheduler.interval_type == "after_sub":
                scheduler.mail_state = "running"
            # global event based
            elif scheduler.mail_done:
                scheduler.mail_state = "sent"
            else:
                scheduler.mail_state = "scheduled"

    def execute(self):
        now = fields.Datetime.now()
        for scheduler in self._filter_template_ref():
            if scheduler.interval_type == "after_sub":
                scheduler._execute_attendee_based()
            elif scheduler.event_id.is_multi_slots:
                scheduler._execute_slot_based()
            else:
                # before or after event -> one shot communication, once done skip
                if scheduler.mail_done:
                    continue
                # do not send emails if the mailing was scheduled before the event but the event is over
                if scheduler.scheduled_date <= now and (
                    scheduler.interval_type not in ("before_event", "after_event_start")
                    or scheduler.event_id.date_end > now
                ):
                    scheduler._execute_event_based()
            scheduler.error_datetime = False
        return True

    def _execute_event_based(self, mail_slot=False):
        """Main scheduler method when running in event-based mode aka
        'after_event' or 'before_event' (and their negative counterparts).
        This is a global communication done once i.e. we do not track each
        registration individually.

        :param mail_slot: optional <event.mail.slot> slot-specific event communication,
          when event uses slots. In that case, it works like the classic event
          communication (iterative, ...) but information is specific to each
          slot (last registration, scheduled datetime, ...)
        """
        auto_commit = not modules.module.current_test
        batch_size, cron_limit = self._get_scheduler_batch_limits()
        scheduler_record = mail_slot or self

        # fetch registrations to contact
        registration_domain = [
            ("event_id", "=", self.event_id.id),
            ("state", "not in", ["draft", "cancel"]),
        ]
        if mail_slot:
            registration_domain += [("event_slot_id", "=", mail_slot.event_slot_id.id)]
        if scheduler_record.last_registration_id:
            registration_domain += [
                ("id", ">", scheduler_record.last_registration_id.id)
            ]
        registrations = self.env["event.registration"].search(
            registration_domain, limit=(cron_limit + 1), order="id ASC"
        )

        # no registrations -> done
        if not registrations:
            scheduler_record.mail_done = True
            return

        # there are more than planned for the cron -> reschedule
        if len(registrations) > cron_limit:
            registrations = registrations[:cron_limit]
            self.env.ref("event.event_mail_scheduler")._trigger()

        for registrations_chunk in (
            self.env["event.registration"].browse(b)
            for b in batched(registrations.ids, batch_size, strict=False)
        ):
            self._execute_event_based_for_registrations(registrations_chunk)
            scheduler_record.last_registration_id = registrations_chunk[-1]

            self._refresh_mail_count_done(mail_slot=mail_slot)
            if auto_commit:
                self.env.cr.commit()
                # invalidate cache, no need to keep previous content in memory
                self.env.invalidate_all()

    def _execute_event_based_for_registrations(self, registrations):
        """Method doing notification and recipients specific implementation
        of contacting attendees globally.

        :param registrations: a recordset of registrations to contact
        """
        self.check_singleton()
        if self.notification_type == "mail":
            self._send_mail(registrations)
        return True

    def _execute_slot_based(self):
        """Main scheduler method when running in slot-based mode aka
        'after_event' or 'before_event' (and their negative counterparts) on
        events with slots. This is a global communication done once i.e. we do
        not track each registration individually."""
        # create slot-specific schedulers if not existing
        missing_slots = self.event_id.event_slot_ids - self.mail_slot_ids.event_slot_id
        if missing_slots:
            self.write(
                {
                    "mail_slot_ids": [
                        (0, 0, {"event_slot_id": slot.id}) for slot in missing_slots
                    ]
                }
            )

        # filter slots to contact
        now = fields.Datetime.now()
        for mail_slot in self.mail_slot_ids:
            # before or after event -> one shot communication, once done skip
            if mail_slot.mail_done:
                continue
            # do not send emails if the mailing was scheduled before the slot but the slot is over
            if mail_slot.scheduled_date <= now and (
                self.interval_type not in ("before_event", "after_event_start")
                or mail_slot.event_slot_id.end_datetime > now
            ):
                self._execute_event_based(mail_slot=mail_slot)

    def _get_scheduler_batch_limits(self):
        """Return the batch size and cron limit driving attendee-based runs.

        Both fall back to a non-zero default: a batch size of 0 would iterate
        over nothing, and a cron limit of 0 would loop.

        :return: (batch_size, cron_limit)
        :rtype: tuple
        """
        batch_size = (
            int(self.env["ir.config_parameter"].sudo().get_param("mail.batch_size"))
            or 50
        )
        cron_limit = (
            int(
                self.env["ir.config_parameter"]
                .sudo()
                .get_param("mail.render.cron.limit")
            )
            or 1000
        )
        return batch_size, cron_limit

    def _create_missing_attendee_mails(self, context_registrations, cron_limit):
        """Generate the 'event.mail.registration' this scheduler still misses.

        Fillup on subscription lines: generate more than to render, as
        creating mail.registration is less costly than rendering emails.

        :param list context_registrations: Optional registration ids to restrict to
        :param int cron_limit: The cron's own limit; twice that is generated
        :return: The newly created scheduled communications
        :rtype: recordset of `event.mail.registration`
        """
        self.check_singleton()

        # note: original 2many domain was
        #   ("id", "not in", self.env["event.registration"]._search([
        #       ("mail_registration_ids.scheduler_id", "in", self.ids),
        #   ]))
        # but it gives less optimized sql
        new_attendee_domain = [
            ("event_id", "=", self.event_id.id),
            ("state", "not in", ("cancel", "draft")),
            (
                "mail_registration_ids",
                "not in",
                self.env["event.mail.registration"]._search(
                    [("scheduler_id", "in", self.ids)]
                ),
            ),
        ]
        if context_registrations:
            new_attendee_domain += [
                ("id", "in", context_registrations),
            ]
        self.env["event.mail.registration"].flush_model(
            ["registration_id", "scheduler_id"]
        )
        new_attendees = self.env["event.registration"].search(
            new_attendee_domain, limit=cron_limit * 2, order="id ASC"
        )
        return self._create_missing_mail_registrations(new_attendees)

    def _get_attendee_mails_to_run(
        self, new_attendee_mails, context_registrations, cron_limit
    ):
        """Return the scheduled communications this run should send.

        When more than the cron limit are due, the surplus is left for a
        re-triggered cron rather than handled in one pass.

        :param recordset new_attendee_mails: The communications just generated
        :param list context_registrations: Optional registration ids to restrict to
        :param int cron_limit: The most to handle in one run
        :return: The communications to run, capped at `cron_limit`
        :rtype: recordset of `event.mail.registration`
        """
        self.check_singleton()

        mail_domain = self.env["event.mail.registration"]._get_domain_skip() + [
            ("scheduler_id", "=", self.id)
        ]
        if context_registrations:
            new_attendee_mails = new_attendee_mails.filtered_domain(mail_domain)
        else:
            new_attendee_mails = self.env["event.mail.registration"].search(
                mail_domain, limit=(cron_limit + 1), order="id ASC"
            )

        # there are more than planned for the cron -> reschedule
        if len(new_attendee_mails) > cron_limit:
            new_attendee_mails = new_attendee_mails[:cron_limit]
            self.env.ref("event.event_mail_scheduler")._trigger()

        return new_attendee_mails

    def _execute_attendee_mail_batches(
        self, new_attendee_mails, batch_size, auto_commit
    ):
        """Send `new_attendee_mails` in batches, committing between them.

        :param recordset new_attendee_mails: The communications to run
        :param int batch_size: How many to handle per batch
        :param bool auto_commit: Whether to commit between batches
        :return: None
        """
        self.check_singleton()

        for chunk in (
            self.env["event.mail.registration"].browse(b)
            for b in batched(new_attendee_mails.ids, batch_size, strict=False)
        ):
            # filter out canceled / draft, and compare to seats_taken (same heuristic)
            valid_chunk = chunk.filtered(
                lambda m: m.registration_id.state not in ("draft", "cancel")
            )
            # scheduled mails for draft / cancel should be removed as they won't be sent
            (chunk - valid_chunk).unlink()

            # send communications, then refresh the counters. The guard that
            # once skipped this outside cron mode is gone: mail_done is derived
            # from the count, so skipping it left an on-subscription scheduler
            # reporting a stale total.
            valid_chunk._execute_on_registrations()
            self._refresh_mail_count_done()
            if auto_commit:
                self.env.cr.commit()
                # invalidate cache, no need to keep previous content in memory
                self.env.invalidate_all()

    def _execute_attendee_based(self):
        """Main scheduler method when running in attendee-based mode aka
        'after_sub'. This relies on a sub model allowing to know which
        registrations have been contacted.

        It currently does two main things
          * generate missing 'event.mail.registrations' which are scheduled
            communication linked to registrations;
          * launch registration-based communication, splitting in batches as
            it may imply a lot of computation. When having more than given
            limit to handle, schedule another call of cron to avoid having to
            wait another cron interval check;
        """
        self.check_singleton()
        context_registrations = self.env.context.get("event_mail_registration_ids")

        auto_commit = not modules.module.current_test
        batch_size, cron_limit = self._get_scheduler_batch_limits()

        new_attendee_mails = self._create_missing_attendee_mails(
            context_registrations, cron_limit
        )
        new_attendee_mails = self._get_attendee_mails_to_run(
            new_attendee_mails, context_registrations, cron_limit
        )
        self._execute_attendee_mail_batches(new_attendee_mails, batch_size, auto_commit)

    def _create_missing_mail_registrations(self, registrations):
        new = self.env["event.mail.registration"]
        for scheduler in self:
            for chunk in batched(registrations.ids, 500, strict=False):
                new += self.env["event.mail.registration"].create(
                    [
                        {
                            "registration_id": registration_id,
                            "scheduler_id": scheduler.id,
                        }
                        for registration_id in chunk
                    ]
                )
        return new

    def _refresh_mail_count_done(self, mail_slot=False):
        for scheduler in self:
            if scheduler.interval_type == "after_sub":
                total_sent = self.env["event.mail.registration"].search_count(  # noqa: E8507 - one count per scheduler, on its own registrations
                    [
                        ("scheduler_id", "=", scheduler.id),
                        ("mail_sent", "=", True),
                    ]
                )
                scheduler.mail_count_done = total_sent
            elif mail_slot and mail_slot.last_registration_id:
                total_sent = self.env["event.registration"].search_count(  # noqa: E8507 - one count per scheduler, on its own registrations
                    [
                        ("id", "<=", mail_slot.last_registration_id.id),
                        ("event_id", "=", scheduler.event_id.id),
                        ("event_slot_id", "=", mail_slot.event_slot_id.id),
                        ("state", "not in", ["draft", "cancel"]),
                    ]
                )
                mail_slot.mail_count_done = total_sent
                mail_slot.mail_done = total_sent >= mail_slot.event_slot_id.seats_taken
                scheduler.mail_count_done = sum(
                    scheduler.mail_slot_ids.mapped("mail_count_done")
                )
                scheduler.mail_done = (
                    scheduler.mail_count_done >= scheduler.event_id.seats_taken
                )
            elif scheduler.last_registration_id:
                total_sent = self.env["event.registration"].search_count(  # noqa: E8507 - one count per scheduler, on its own registrations
                    [
                        ("id", "<=", scheduler.last_registration_id.id),
                        ("event_id", "=", scheduler.event_id.id),
                        ("state", "not in", ["draft", "cancel"]),
                    ]
                )
                scheduler.mail_count_done = total_sent
                scheduler.mail_done = total_sent >= scheduler.event_id.seats_taken
            else:
                scheduler.mail_count_done = 0
                scheduler.mail_done = False

    def _filter_template_ref(self):
        """Check for valid template reference: existing, working template"""
        type_info = self._template_model_by_notification_type()

        if not self:
            return self.browse()

        invalid = self.browse()
        missing = self.browse()
        for scheduler in self:
            tpl_model = type_info[scheduler.notification_type]
            if scheduler.template_ref._name != tpl_model:
                invalid += scheduler
            else:
                template = (
                    self.env[tpl_model].browse(scheduler.template_ref.id).exists()
                )
                if not template:
                    missing += scheduler
        for scheduler in missing:
            _logger.warning(
                "Cannot process scheduler %s (event %s - ID %s) as it refers to non-existent %s (ID %s)",
                scheduler.id,
                scheduler.event_id.name,
                scheduler.event_id.id,
                type_info[scheduler.notification_type],
                scheduler.template_ref.id,
            )
        for scheduler in invalid:
            _logger.warning(
                "Cannot process scheduler %s (event %s - ID %s) as it refers to invalid template %s (ID %s) (%s instead of %s)",
                scheduler.id,
                scheduler.event_id.name,
                scheduler.event_id.id,
                scheduler.template_ref.name,
                scheduler.template_ref.id,
                scheduler.template_ref._name,
                type_info[scheduler.notification_type],
            )
        return self - missing - invalid

    def _send_mail(self, registrations):
        """Mail action: send mail to attendees"""
        if self.event_id.organizer_id.email:
            author = self.event_id.organizer_id
        elif self.env.company.email:
            author = self.env.company.partner_id
        elif self.env.user.email:
            author = self.env.user.partner_id
        else:
            author = self.env.ref("base.user_root").partner_id

        composer_values = {
            "composition_mode": "mass_mail",
            "force_send": False,
            "model": registrations._name,
            "res_ids": registrations.ids,
            "template_id": self.template_ref.id,
        }
        # force author, as mailing mode does not try to find the author matching
        # email_from (done only when posting on chatter); give email_from if not
        # configured on template
        composer_values["author_id"] = author.id
        composer_values["email_from"] = (
            self.template_ref.email_from or author.email_formatted
        )
        composer = self.env["mail.compose.message"].create(composer_values)
        # backward compatible behavior: event mail scheduler does not force partner
        # creation, email_cc / email_to is kept on outgoing emails
        composer.with_context(mail_composer_force_partners=False)._action_send_mail()

    def _warn_error(self, exception):
        last_error_dt = self.error_datetime
        now = self.env.cr.now().replace(microsecond=0)
        if not last_error_dt or last_error_dt < now - relativedelta(hours=1):
            # message base: event, date
            event, template = self.event_id, self.template_ref
            if self.interval_type == "after_sub":
                scheduled_date = now
            else:
                scheduled_date = self.scheduled_date
            body_content = _(
                "Communication for %(event_name)s scheduled on %(scheduled_date)s failed.",
                event_name=event.name,
                scheduled_date=scheduled_date,
            )

            # add some information on cause
            template_link = Markup('<a href="%s">%s (%s)</a>') % (
                f"{self.get_base_url()}/odoo/{template._name}/{template.id}",
                template.display_name,
                template.id,
            )
            cause = exception.__cause__ or exception.__context__
            if hasattr(cause, "qweb"):
                source_content = _(
                    "This is due to an error in template %(template_link)s.",
                    template_link=template_link,
                )
                if isinstance(cause, QWebError) and isinstance(
                    cause.__cause__, AttributeError
                ):
                    error_message = _(
                        "There is an issue with dynamic placeholder. Actual error received is: %(error)s.",
                        error=Markup("<br/>%s") % cause.__cause__,
                    )
                else:
                    error_message = _(
                        "Rendering of template failed with error: %(error)s.",
                        error=Markup("<br/>%s") % cause.qweb,
                    )
            else:
                source_content = _(
                    "This may be linked to template %(template_link)s.",
                    template_link=template_link,
                )
                error_message = _(
                    "It failed with error %(error)s.",
                    error=str(exception),
                )

            body = Markup("<p>%s %s<br /><br />%s</p>") % (
                body_content,
                source_content,
                error_message,
            )
            recipients = (
                event.organizer_id
                | event.user_id.partner_id
                | template.write_uid.partner_id
            ).filtered(lambda p: p.active)
            self.event_id.message_post(
                body=body,
                force_send=False,  # use email queue, especially it could be cause of error
                notify_author_mention=True,  # in case of event responsible creating attendees
                partner_ids=recipients.ids,
            )
            self.error_datetime = now

    @api.model
    def run(self, autocommit=False):
        """Backward compatible method, notably if crons are not updated when
        migrating for some reason."""
        return self.schedule_communications(autocommit=autocommit)

    @api.model
    def schedule_communications(self, autocommit=False):
        schedulers = self.search(
            [
                # skip archived events
                ("event_id.active", "=", True),
                # skip if event is cancelled
                ("event_id.kanban_state", "!=", "cancel"),
                # scheduled
                ("scheduled_date", "<=", fields.Datetime.now()),
                # event-based: todo / attendee-based: running until event is not done
                ("mail_done", "=", False),
                "|",
                ("interval_type", "!=", "after_sub"),
                ("event_id.date_end", ">", self.env.cr.now()),
            ]
        )

        for scheduler in schedulers:
            try:
                # Prevent a mega prefetch of the registration ids of all the events of all the schedulers
                self.browse(scheduler.id).execute()
            except Exception as e:
                _logger.exception(
                    "Error while executing event mail scheduler %s", scheduler.id
                )
                self.env.invalidate_all()
                scheduler._warn_error(e)
            else:
                if autocommit and not modules.module.current_test:
                    self.env.cr.commit()
        return True

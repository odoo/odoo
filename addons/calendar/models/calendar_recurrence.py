from datetime import UTC

from dateutil.relativedelta import relativedelta

from odoo import api, fields, models
from odoo.fields import Domain
from odoo.tools.misc import clean_context


class CalendarRecurrence(models.Model):
    _name = "calendar.recurrence"
    _inherit = ["mixin.calendar.privacy", "mixin.recurrence.rrule"]
    _description = "Event Recurrence Rule"

    _privacy_event_fname = "calendar_event_ids"
    _search_visibility_fields = ("calendar_event_ids",)

    base_event_id = fields.Many2one(
        comodel_name="calendar.event",
        copy=False,
        ondelete="set null",
    )  # store=False ?
    calendar_event_ids = fields.One2many(
        comodel_name="calendar.event",
        inverse_name="recurrence_id",
    )
    trigger_id = fields.Many2one(comodel_name="ir.cron.trigger")

    # ------------------------------------------------------------
    # PRIVACY
    # ------------------------------------------------------------

    @api.model
    def _get_domain_privacy(self):
        # The link is an x2many, so the mixin's `any` default would search the
        # comodel with the field's own context and drop recurrences whose events
        # are all archived -- exactly the ones `action_mass_archive` produces.
        # Select through the events instead, with active_test off.
        events = self.env["calendar.event"].with_context(active_test=False)
        visible = events._search(
            Domain(events._get_domain_default_privacy()),
            active_test=False,
        )
        # A recurrence with no events yet protects nothing, and it is a state the
        # machinery passes through: `_apply_recurrence_values` creates the
        # recurrence and only then hangs events off it, so a guard that looked
        # only at the events denied the creator access to the record they had
        # just created (`microsoft_sync.write` reading `need_sync_m` on it was
        # the first casualty).
        return Domain("calendar_event_ids", "=", False) | Domain(
            "id", "in", visible.select("recurrence_id")
        )

    def _check_calendar_privacy_write_permissions(self):
        """Refuse writes on a recurrence whose events the user may not see.

        `calendar.attendee` gets this for free -- its own `write` already calls
        `event_id.check_access('write')`. A recurrence had no such check, so any
        employee could rewrite the repetition rule of another user's private
        event even though every event in it refused the same write.
        """
        if self.env.su:
            return
        hidden = self._privacy_hidden()
        if hidden:
            raise self.env["ir.rule"]._prepare_access_error("write", hidden[0])

    @api.model_create_multi
    def create(self, vals_list):
        recurrences = super().create(vals_list)
        recurrences._check_calendar_privacy_write_permissions()
        return recurrences

    def write(self, vals):
        self._check_calendar_privacy_write_permissions()
        return super().write(vals)

    def unlink(self):
        self._check_calendar_privacy_write_permissions()
        return super().unlink()

    @api.depends("calendar_event_ids.start")
    def _compute_dtstart(self):
        groups = self.env["calendar.event"]._read_group(
            [("recurrence_id", "in", self.ids)], ["recurrence_id"], ["start:min"]
        )
        start_mapping = {recurrence.id: start_min for recurrence, start_min in groups}
        for recurrence in self:
            recurrence.dtstart = start_mapping.get(recurrence.id)

    def _reconcile_events(self, ranges):
        """
        :param ranges: iterable of tuples (datetime_start, datetime_stop)
        :return: tuple (events of the recurrence already in sync with ranges,
                 and ranges not covered by any events)
        """
        ranges = set(ranges)

        synced_events = self.calendar_event_ids.filtered(lambda e: e._range() in ranges)

        existing_ranges = {event._range() for event in synced_events}
        ranges_to_create = (
            event_range for event_range in ranges if event_range not in existing_ranges
        )
        return synced_events, ranges_to_create

    def _select_new_base_event(self):
        """
        when the base event is no more available (archived, deleted, etc.), a new one should be selected
        """
        for recurrence in self:
            recurrence.base_event_id = recurrence._get_first_event()

    def _apply_recurrence(
        self,
        specific_values_creation=None,
        no_send_edit=False,
        generic_values_creation=None,
    ):
        """Create missing events in the recurrence and detach events which no longer
        follow the recurrence rules.
        :return: detached events
        """
        event_vals = []
        keep = self.env["calendar.event"]
        if specific_values_creation is None:
            specific_values_creation = {}

        for recurrence in self.filtered("base_event_id"):
            recurrence.calendar_event_ids |= recurrence.base_event_id
            # `or recurrence._get_first_event(include_outliers=False)` stood
            # here: unreachable behind the `filtered("base_event_id")` above,
            # and reaching it would have enumerated the whole rrule to work out
            # which events are outliers.
            event = recurrence.base_event_id
            duration = event.stop - event.start
            if specific_values_creation:
                ranges = {
                    (x[1], x[2])
                    for x in specific_values_creation
                    if x[0] == recurrence.id
                }
            else:
                ranges = recurrence._range_calculation(event.start, duration)

            events_to_keep, ranges = recurrence._reconcile_events(ranges)
            keep |= events_to_keep
            [base_values] = event.copy_data()
            values = []
            for start, stop in ranges:
                value = dict(
                    base_values,
                    start=start,
                    stop=stop,
                    recurrence_id=recurrence.id,
                    follow_recurrence=True,
                )
                if (recurrence.id, start, stop) in specific_values_creation:
                    value.update(specific_values_creation[(recurrence.id, start, stop)])
                if generic_values_creation and recurrence.id in generic_values_creation:
                    value.update(generic_values_creation[recurrence.id])
                values += [value]
            event_vals += values

        events = self.calendar_event_ids - keep
        detached_events = self._detach_events(events)
        context = {
            **clean_context(self.env.context),
            "no_mail_to_attendees": True,
            "mail_create_nolog": True,
        }
        self.env["calendar.event"].with_context(context).create(event_vals)
        return detached_events

    def _schedule_next_occurrence_alarm(self, recurrence_update=False):
        """Schedule one cron trigger per recurrence, for its next occurrence.

        Named apart from `calendar.event._setup_alarms`, which it calls: that one
        schedules a trigger for each event it is given and hands back the ids,
        while this one picks the single next future occurrence of each recurrence
        and remembers its trigger on the recurrence. Both used to be spelled
        `_setup_alarms`, so `self.recurrence_id._setup_alarms()` beside
        `self._setup_alarms()` read as the same operation on two objects.

        :param recurrence_update: boolean: if true, update all recurrences in self, else only the recurrences
               without trigger
        """
        now = self.env.context.get("date") or fields.Datetime.now()
        # get next events
        self.env["calendar.event"].flush_model(fnames=["recurrence_id", "start"])
        if not self.calendar_event_ids.ids:
            return

        self.env.cr.execute(
            """
            SELECT DISTINCT ON (recurrence_id) id event_id, recurrence_id
                    FROM calendar_event
                   WHERE start > %s
                     AND id = ANY(%s)
                ORDER BY recurrence_id,start ASC;
        """,
            (now, list(self.calendar_event_ids.ids)),
        )
        result = self.env.cr.dictfetchall()
        if not result:
            return
        events = self.env["calendar.event"].browse(
            value["event_id"] for value in result
        )
        triggers_by_events = events._setup_alarms()
        for vals in result:
            trigger_id = triggers_by_events.get(vals["event_id"])
            if not trigger_id:
                continue
            recurrence = self.env["calendar.recurrence"].browse(vals["recurrence_id"])
            recurrence.trigger_id = trigger_id

    def _split_from(self, event, recurrence_values=None):
        """Stops the current recurrence at the given event and creates a new one starting
        with the event.
        :param event: starting point of the new recurrence
        :param recurrence_values: values applied to the new recurrence
        :return: new recurrence
        """
        if recurrence_values is None:
            recurrence_values = {}
        event.check_singleton()
        if not self:
            return None
        [values] = self.copy_data()
        detached_events = self._stop_at(event)

        repeat_number = recurrence_values.get("repeat_number", 0) or len(
            detached_events
        )
        return self.create(
            {
                **values,
                **recurrence_values,
                "base_event_id": event.id,
                "calendar_event_ids": [(6, 0, detached_events.ids)],
                "repeat_number": max(repeat_number, 1),
            }
        )

    def _stop_at(self, event):
        """Stops the recurrence at the given event. Detach the event and all following
        events from the recurrence.

        :return: detached events from the recurrence
        """
        self.check_singleton()
        events = self._get_events_from(event.start)
        detached_events = self._detach_events(events)
        if not self.calendar_event_ids:
            self.with_context(archive_on_error=True).unlink()
            return detached_events

        if event.allday:
            until = self._get_start_of_period(event.start_date)
        else:
            until_datetime = self._get_start_of_period(event.start)
            until_timezoned = until_datetime.replace(tzinfo=UTC).astimezone(
                self._get_timezone()
            )
            until = until_timezoned.date()
        self.write(
            {
                "repeat_type": "until",
                "repeat_until": until - relativedelta(days=1),
            }
        )
        return detached_events

    @api.model
    def _detach_events(self, events):
        events.with_context(dont_notify=True).write(
            {
                "recurrence_id": False,
                "recurrency": True,
            }
        )
        return events

    def _write_events(self, values, dtstart=None):
        """
        Write values on events in the recurrence.
        :param values: event values
        :param dtstart: if provided, only write events starting from this point in time
        """
        events = self._get_events_from(dtstart) if dtstart else self.calendar_event_ids
        return events.with_context(no_mail_to_attendees=True, dont_notify=True).write(
            dict(values, recurrence_update="this")
        )

    def _get_first_event(self, include_outliers=False):
        if not self.calendar_event_ids:
            return self.env["calendar.event"]
        events = self.calendar_event_ids.sorted("start")
        if not include_outliers:
            events -= self._get_outliers()
        return events[:1]

    def _get_outliers(self):
        synced_events = self.env["calendar.event"]
        for recurrence in self:
            if recurrence.calendar_event_ids:
                start = min(recurrence.calendar_event_ids.mapped("start"))
                starts = set(recurrence._get_occurrences(start))
                synced_events |= recurrence.calendar_event_ids.filtered(
                    lambda e: e.start in starts  # noqa: B023 - filtered() is invoked eagerly within this same loop iteration, not deferred
                )
        return self.calendar_event_ids - synced_events

    def _get_events_from(self, dtstart):
        """Occurrences of this recurrence starting at or after `dtstart`.

        Archived ones included. This filtered them out **twice** -- reading the
        one2many applies the comodel's active test, and then so does the search
        -- so an archived occurrence after the cut point was neither detached
        nor deleted by anything built on this: `_stop_at`, and through it
        `action_mass_archive`, `action_mass_deletion` and `_break_recurrence`.

        Deleting "this and following" therefore left an archived occurrence
        behind, still pointing at a recurrence whose rule now ends before it
        starts. Being archived is not being outside the series -- `_stop_at`
        archives occurrences itself, so the state is one this module produces.
        """
        events = self.with_context(active_test=False).calendar_event_ids
        return (
            self.env["calendar.event"]
            .with_context(active_test=False)
            .search([("id", "in", events.ids), ("start", ">=", dtstart)])
        )

    def _is_allday(self):
        """Returns whether a majority of events are allday or not (there might be some outlier events).

        Ties (as many allday as non-allday outliers) resolve to allday: `>=`,
        not `>`, is deliberate here, not an oversight.
        """
        score = sum(1 if e.allday else -1 for e in self.calendar_event_ids)
        return score >= 0

    def _is_event_over(self):
        """Check if all events in this recurrence are in the past.

        Shares its name with `calendar.event._is_event_over` on purpose, not by
        accident: `mixin.google.calendar.sync` is mixed into both models and
        `_google_patch` asks `self._is_event_over()` without knowing which one
        it is holding. Same question, different object -- an event is over when
        it is past, a recurrence when every event in it is. Do not rename either
        half without the other and that call site.

        :return: True if all events are over, False otherwise
        """
        self.check_singleton()
        if not self.calendar_event_ids:
            return False

        now = fields.Datetime.now()
        today = fields.Date.today()

        return all(
            (event.stop_date < today if event.allday else event.stop < now)
            for event in self.calendar_event_ids
        )

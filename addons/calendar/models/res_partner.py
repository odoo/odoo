from collections import defaultdict
from datetime import UTC, datetime, timedelta

from odoo import _, api, fields, models
from odoo.fields import Domain
from odoo.tools import SQL


class ResPartner(models.Model):
    _inherit = "res.partner"

    meeting_count = fields.Integer(
        string="# Meetings",
        compute="_compute_meeting_count",
    )
    meeting_ids = fields.Many2many(
        comodel_name="calendar.event",
        relation="calendar_event_res_partner_rel",
        column1="res_partner_id",
        column2="calendar_event_id",
        string="Meetings",
        copy=False,
    )

    calendar_last_notif_ack = fields.Datetime(
        string="Last notification marked as read from base Calendar",
        default=fields.Datetime.now,
    )

    def _get_calendar_event_resources(self, company=None):
        """Resolve people in one query: this company's resource, else a shared one, else any.

        A person is a human resource through their party, so an attendee with no
        user — an outside contractor, an employee with no login — resolves exactly
        like one who has a login. A person attends a meeting once, so the last
        fallback books the resource they have elsewhere rather than nothing.
        """
        company = company or self.env.company
        resources = (
            self.env["resource.resource"]
            .sudo()
            .search_fetch(
                [("partner_id", "in", self.ids), ("resource_type", "=", "user")],
                ["partner_id", "company_id"],
                order="id",
            )
        )
        by_partner = resources.grouped("partner_id")
        return {
            partner: by_partner.get(partner, resources.browse()).sorted(
                key=lambda resource: (
                    0
                    if resource.company_id == company
                    else 1
                    if not resource.company_id
                    else 2
                )
            )[:1]
            for partner in self
        }

    def _compute_meeting_count(self):
        result = self._get_meetings_by_partner()
        for p in self:
            p.meeting_count = len(result.get(p.id, []))

    def _get_meetings_by_partner(self):
        if self.ids:
            # prefetch 'parent_id'
            all_partners = self.with_context(active_test=False).search_fetch(
                [("id", "child_of", self.ids)],
                ["parent_id"],
            )

            query = self.env["calendar.event"]._search([])  # ir.rules will be applied
            meeting_data = self.env.execute_query(
                SQL(
                    """
                SELECT DISTINCT res_partner_id, calendar_event_id
                  FROM calendar_event_res_partner_rel
                 WHERE res_partner_id = ANY(%s) AND calendar_event_id IN %s
                """,
                    list(all_partners._ids),
                    query.subselect(),
                )
            )

            # Create a dict {partner_id: event_ids} and fill with events linked to the partner
            meetings = {}
            for p_id, m_id in meeting_data:
                meetings.setdefault(p_id, set()).add(m_id)

            # Roll each partner's meetings up to whichever of its ancestors are
            # in `self`. `in self` is a scan of the recordset, and it sat inside
            # a walk up the parent chain of every partner that had a meeting, so
            # the cost was O(partners x depth x len(self)); the ids are known up
            # front.
            wanted_ids = set(self._ids)
            for p in self.browse(meetings.keys()):
                partner = p
                while partner.parent_id:
                    partner = partner.parent_id
                    if partner.id in wanted_ids:
                        meetings[partner.id] = (
                            meetings.get(partner.id, set()) | meetings[p.id]
                        )
            return {p_id: list(meetings.get(p_id, set())) for p_id in self.ids}
        return {}

    def _get_application_statistics(self):
        data_list = super()._get_application_statistics()
        for partner in self.filtered("meeting_count"):
            stat_info = {
                "iconClass": "fa-solid fa-calendar",
                "value": partner.meeting_count,
                "label": _("Meetings"),
                "tagClass": "o_tag_color_3",
            }
            data_list[partner.id].append(stat_info)
        return data_list

    def get_attendee_detail(self, meeting_ids):
        """Return a list of dict of the given meetings with the attendees details
        Used by:

        - many2many_attendee.js: Many2ManyAttendee
        - calendar_model.js (calendar.CalendarModel)
        """
        attendees_details = []
        meetings = self.env["calendar.event"].browse(meeting_ids)
        for attendee in meetings.attendee_ids:
            if attendee.partner_id not in self:
                continue
            attendee_is_organizer = (
                self.env.user == attendee.event_id.user_id
                and attendee.partner_id == self.env.user.partner_id
            )
            attendees_details.append(
                {
                    "id": attendee.partner_id.id,
                    "name": attendee.partner_id.display_name,
                    "status": attendee.state,
                    "event_id": attendee.event_id.id,
                    "attendee_id": attendee.id,
                    "is_alone": attendee.event_id.is_organizer_alone
                    and attendee_is_organizer,
                    # attendees data is sorted according to this key in JS.
                    "is_organizer": 1
                    if attendee.partner_id == attendee.event_id.user_id.partner_id
                    else 0,
                }
            )
        return attendees_details

    @api.model
    def _set_calendar_last_notif_ack(self):
        """Stamp the calling user's reminder acknowledgement."""
        # `self.env.user`, not `self.env.context.get('uid', ...)`: the route calls
        # this through sudo(), and taking the identity from a context key means
        # any caller able to set `uid` in the context stamps somebody else's
        # partner. `fields.Datetime.now()` rather than `datetime.now()` for the
        # same reason every other write of this column uses it -- the two agree
        # today, and the field's own default is already spelled this way.
        self.env.user.partner_id.write(
            {
                "calendar_last_notif_ack": fields.Datetime.now(),
            }
        )

    def schedule_meeting(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "calendar.action_calendar_event"
        )
        # Not `partner_ids = self.ids; partner_ids.append(...)`: that reads as a
        # mutation of the recordset's own ids and is only safe because `ids`
        # happens to build a fresh list each time.
        action["context"] = {
            "default_partner_ids": [*self.ids, self.env.user.partner_id.id],
        }
        # The first branch carries the meetings of this partner's *children*,
        # which the second cannot express as a domain.
        action["domain"] = [
            "|",
            ("id", "in", self._get_meetings_by_partner()[self.id]),
            ("partner_ids", "in", self.ids),
        ]
        return action

    def _get_busy_calendar_events(self, start_datetime, end_datetime):
        """Get a mapping from partner id to attended events intersecting with the time interval.

        :rtype: dict[int, <calendar.event>]
        """
        return self._group_busy_calendar_events(
            self._search_busy_calendar_events(start_datetime, end_datetime),
            start_datetime,
            end_datetime,
        )

    def _search_busy_calendar_events(self, start_datetime, end_datetime):
        """Fetch candidate busy events once, including all-day civil-date ranges."""
        start = self._calendar_utc(start_datetime)
        stop = self._calendar_utc(end_datetime)
        if start >= stop:
            return self.env["calendar.event"]
        timed = Domain.AND(
            [
                Domain("allday", "=", False),
                Domain("start", "<", stop),
                Domain("stop", ">", start),
            ]
        )
        # Civil dates can be on either side of UTC for the attendee's timezone.
        # Exact clipping happens after fetching, using the same normalization as
        # reservation projection, rather than the stored 08:00-18:00 placeholders.
        all_day = Domain.AND(
            [
                Domain("allday", "=", True),
                Domain("start_date", "<=", stop.date() + timedelta(days=1)),
                Domain("stop_date", ">=", start.date() - timedelta(days=1)),
            ]
        )
        domain = Domain.AND(
            [
                Domain("partner_ids", "in", self.ids),
                Domain("show_as", "=", "busy"),
                timed | all_day,
            ]
        )
        if ignored := self.env.context.get("ignore_event_ids"):
            domain &= Domain("id", "not in", ignored)
        return self.env["calendar.event"].search_fetch(
            domain,
            ["start", "stop", "allday", "start_date", "stop_date"],
            order="start, id",
        )

    @staticmethod
    def _calendar_utc(value):
        """Normalize aware instants to stored UTC; naive inputs already mean UTC."""
        return value.astimezone(UTC).replace(tzinfo=None) if value.tzinfo else value

    def _group_busy_calendar_events(self, events, start_datetime, end_datetime):
        intervals = self._group_busy_calendar_intervals(
            events, start_datetime, end_datetime
        )
        return {
            partner_id: self.env["calendar.event"].union(
                *(event for _, _, event in values)
            )
            for partner_id, values in intervals.items()
        }

    def _get_busy_calendar_intervals(
        self, start_datetime, end_datetime, *, user_resources=None
    ):
        """Return attended busy intervals in UTC, keyed by requested partner id."""
        return self._group_busy_calendar_intervals(
            self._search_busy_calendar_events(start_datetime, end_datetime),
            start_datetime,
            end_datetime,
            user_resources=user_resources,
        )

    def _group_busy_calendar_intervals(
        self, events, start_datetime, end_datetime, *, user_resources=None
    ):
        """Normalize civil days once for availability checks and presentation alike."""
        start = self._calendar_utc(start_datetime)
        stop = self._calendar_utc(end_datetime)
        if start >= stop:
            return {}
        resources_by_partner = defaultdict(lambda: self.env["resource.resource"])
        if user_resources is None:
            attendees = events.filtered("allday").partner_ids & self
            for partner, resource in (
                attendees._get_calendar_event_resources() if attendees else {}
            ).items():
                resources_by_partner[partner.id] |= resource
        else:
            for user, resource in user_resources.items():
                resources_by_partner[user.partner_id.id] |= resource
        grouped = defaultdict(list)
        for event in events:
            if not event.active or event.show_as != "busy":
                continue
            for partner in event.partner_ids & self:
                for event_start, event_stop in event._get_attendee_intervals(
                    partner,
                    resources=resources_by_partner[partner.id],
                ):
                    if event_start < stop and event_stop > start:
                        grouped[partner.id].append((event_start, event_stop, event))
        return dict(grouped)

    def _is_calendar_available(self, date_start, date_end, appointment_type=None):
        """Check attended meetings while preserving offer-specific sharing policy.

        Equipment-booking customers may book multiple resources concurrently;
        resource admission is checked separately. A same-offer staff booking is
        subject to that offer's capacity calculation rather than an exclusive
        meeting veto. Interval and RSVP semantics come solely from Calendar.
        """
        grouped = self._get_busy_calendar_events(date_start, date_end)
        for partner in self:
            for event in grouped.get(partner.id, self.env["calendar.event"]):
                if (
                    appointment_type
                    and self <= appointment_type.staff_user_ids.partner_id
                    and event.appointment_type_id == appointment_type
                ):
                    continue
                return False
        return True

    upcoming_appointment_ids = fields.Many2many(
        comodel_name="calendar.event",
        string="Upcoming Appointments",
        compute="_compute_upcoming_appointment_ids",
    )

    def _compute_upcoming_appointment_ids(self):
        partner_upcoming_appointments = dict(
            self.env["calendar.event"]._read_group(
                [
                    ("appointment_booker_id", "in", self.ids),
                    ("appointment_type_id", "!=", False),
                    ("start", ">", datetime.now()),
                ],
                ["appointment_booker_id"],
                ["id:recordset"],
            )
        )
        for partner in self:
            partner.upcoming_appointment_ids = partner_upcoming_appointments.get(
                partner, False
            )

import itertools
import logging
import math
import re
from collections import Counter
from datetime import UTC, datetime, time, timedelta
from itertools import repeat
from typing import NamedTuple
from urllib.parse import urlsplit, urlunsplit

from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command, Domain
from odoo.libs.datetime import timezone
from odoo.libs.intervals import intervals_overlap
from odoo.tools import html2plaintext, html_sanitize, is_html_empty, single_email_re
from odoo.tools.misc import get_lang
from odoo.tools.translate import _

from odoo.addons.base.models.mixin_recurrence_rrule import (
    BYDAY_SELECTION,
    MONTH_BY_SELECTION,
    REPEAT_TYPE_SELECTION_RRULE,
    WEEKDAY_SELECTION,
    weekday_to_field,
)
from odoo.addons.base.models.mixin_recurrence_rule import (
    REPEAT_UNIT_SELECTION,
)
from odoo.addons.base.models.res_partner import _selection_timezones
from odoo.addons.calendar.models.calendar_attendee import CalendarAttendee
from odoo.addons.calendar.models.utils import (
    generate_calendar_token,
)

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    _logger.warning(
        "`vobject` Python module not found, iCal file generation disabled. Consider installing this module if you want to generate iCal files"
    )
    vobject = None

# The quick picker above the custom rule. Its four real values are the shared
# `repeat_unit` ones, so `_compute_recurrence` can hand one straight to the
# recurrence instead of translating between two spellings of "weekly".
REPEAT_UNIT_SELECTION_UI = [
    ("day", "Daily"),
    ("week", "Weekly"),
    ("month", "Monthly"),
    ("year", "Yearly"),
    ("custom", "Custom"),
]


def get_weekday_occurence(date):
    """
    :returns: ocurrence

    >>> get_weekday_occurence(date(2019, 12, 17))
    3  # third Tuesday of the month

    >>> get_weekday_occurence(date(2019, 12, 25))
    -1  # last Friday of the month
    """
    occurence_in_month = math.ceil(date.day / 7)
    if occurence_in_month in {4, 5}:  # fourth or fifth week on the month -> last
        return -1
    return occurence_in_month


class RecurrencePolicy(NamedTuple):
    """Which occurrences of a recurrence a `calendar.event.write` is to touch.

    The four flags used to be four locals threaded through a 146-line `write`,
    recomputed from `recurrence_update` at three different points. Named
    together because they are one decision: `setting` is the raw UI selection,
    the rest are what it means for this particular recordset.
    """

    #: 'this' / 'subsequent' / 'all', or None when no policy
    #: applies -- including when one was asked for on an event with no
    #: recurrence, where it is meaningless.
    setting: str | None
    #: rewrite the series rather than this occurrence alone.
    update: bool
    #: `recurrency=False` is being written: detach rather than rewrite.
    breaking: bool
    #: 'subsequent' asked for from the base event, i.e. from the first
    #: occurrence -- "this and following" is then the whole series, and it takes
    #: the `all` path.
    from_base_event: bool


def _add_ics_date(vevent, name, day):
    prop = vevent.add(name)
    prop.value = day.strftime("%Y%m%d")
    prop.value_param = "DATE"
    prop.isNative = False


class CalendarEvent(models.Model):
    _name = "calendar.event"
    _description = "Calendar Event"
    _order = "start desc"
    _search_visibility_fields = (
        "privacy",
        "user_id",
        "partner_ids",
    )
    _inherit = [
        "mixin.mail.thread",
        "mixin.recurrence.occurrence",
        "mixin.resource.scheduling",
    ]
    _systray_view = "calendar"

    # ``write`` below keeps working long after ``super()`` returns: it applies
    # recurrence values, detaches occurrences, archives part of ``self`` and
    # unlinks the rest.  Worse, the ``update_recurrence`` branch never calls
    # ``super().write()`` on ``self`` at all -- ``_rewrite_recurrence`` and
    # ``_update_future_events`` do the work -- so the mixin's own hook would
    # simply never fire for the edits that move the most bookings.  Project
    # from the end of ``create``/``write`` instead, once the event is settled.
    _reservation_sync_manual = True

    DISCUSS_ROUTE = "calendar/join_videocall"

    @api.model
    def get_state_selections(self):
        return CalendarAttendee.STATE_SELECTION

    @api.model
    def default_get(self, fields):
        # super default_model='crm.lead' for easier use in addons
        context = dict(self.env.context)
        if context.get("default_res_model") and not context.get("default_res_model_id"):
            context.update(
                default_res_model_id=self.env["ir.model"]._get_id(
                    context["default_res_model"]
                )
            )
        if context.get("default_res_model_id") and not context.get("default_res_model"):
            context.update(
                default_res_model=self.env["ir.model"]
                .browse(self.env.context["default_res_model_id"])
                .sudo()
                .model
            )

        defaults = super(CalendarEvent, self.with_context(context)).default_get(fields)

        # support active_model / active_id as replacement of default_* if not already given
        if (
            "res_model_id" not in defaults
            and "res_model_id" in fields
            and context.get("active_model")
            and context["active_model"] != "calendar.event"
        ):
            defaults["res_model_id"] = self.env["ir.model"]._get_id(
                context["active_model"]
            )
            defaults["res_model"] = context.get("active_model")
        if (
            "res_id" not in defaults
            and "res_id" in fields
            and defaults.get("res_model_id")
            and context.get("active_id")
        ):
            defaults["res_id"] = context["active_id"]

        return defaults

    @api.model
    def _default_partner_ids(self):
        """When active_model is res.partner, the current partners should be attendees"""
        partners = self.env.user.partner_id
        active_id = self.env.context.get("active_id")
        if (
            self.env.context.get("active_model") == "res.partner"
            and active_id
            and active_id not in partners.ids
        ):
            partners |= self.env["res.partner"].browse(active_id)
        return partners

    @api.model
    def _default_start(self):
        now = fields.Datetime.now()
        return now + (datetime.min - now) % timedelta(minutes=30)  # noqa: DTZ901 - fields.Datetime.now() is naive (Odoo convention); datetime.min is used only as a naive rounding-arithmetic anchor, not compared for timezone meaning

    @api.model
    def _default_stop(self):
        now = fields.Datetime.now()
        duration_hours = self.get_default_duration()
        start = now + (datetime.min - now) % timedelta(minutes=30)  # noqa: DTZ901 - same reasoning as _default_start
        return start + timedelta(hours=duration_hours)

    # description
    name = fields.Char(
        string="Meeting Subject",
        required=True,
    )
    description = fields.Html(help="""When synchronization with an external calendar is active, this description is synchronized \
        with the one of the associated meeting in that external calendar. Any update will be propagated there \
        and vice versa.""")
    user_id = fields.Many2one(
        comodel_name="res.users",
        string="Organizer",
        default=lambda self: self.env.user,
        index="btree_not_null",
    )
    partner_id = fields.Many2one(
        comodel_name="res.partner",
        related="user_id.partner_id",
        string="Scheduled by",
        readonly=True,
    )
    location = fields.Char(tracking=True)
    notes = fields.Html()  # Unlike description, internal use only
    videocall_location = fields.Char(
        string="Meeting URL",
        compute="_compute_videocall_location",
        store=True,
        copy=True,
    )
    access_token = fields.Char(
        string="Invitation Token",
        store=True,
        index=True,
        copy=False,
    )
    videocall_source = fields.Selection(
        selection=[("discuss", "Discuss"), ("custom", "Custom")],
        compute="_compute_videocall_source",
    )
    videocall_channel_id = fields.Many2one(
        comodel_name="discuss.channel",
        string="Discuss Channel",
        index="btree_not_null",
    )
    # visibility
    privacy = fields.Selection(
        selection=[
            ("public", "Public"),
            ("private", "Private"),
            ("confidential", "Only internal users"),
        ],
        help="People to whom this event will be visible.",
    )
    effective_privacy = fields.Selection(
        selection=[
            ("public", "Public"),
            ("private", "Private"),
            ("confidential", "Only internal users"),
        ],
        compute="_compute_effective_privacy",
        help="Whether the event is private, considering the user privacy",
    )
    show_as = fields.Selection(
        selection=[("free", "Available"), ("busy", "Busy")],
        string="Show as",
        default="busy",
        required=True,
        help="If the time is shown as 'busy', this event will be visible to other people with either the full \
        information or simply 'busy' written depending on its privacy. Use this option to let other people know \
        that you are unavailable during that period of time. \n If the event is shown as 'free', other users know \
        that you are available during that period of time.",
    )
    is_highlighted = fields.Boolean(
        string="Is the Event Highlighted",
        compute="_compute_is_highlighted",
    )
    is_organizer_alone = fields.Boolean(
        string="Is the Organizer Alone",
        compute="_compute_is_organizer_alone",
        help="""Check if the organizer is alone in the event, i.e. if the organizer is the only one that hasn't declined
        the event (only if the organizer is not the only attendee)""",
    )
    # filtering
    active = fields.Boolean(
        default=True,
        tracking=True,
        help="If the active field is set to false, it will allow you to hide the event alarm information without removing it.",
    )
    categ_ids = fields.Many2many(
        comodel_name="calendar.event.type",
        relation="meeting_category_rel",
        column1="event_id",
        column2="type_id",
        string="Tags",
    )
    # timing
    start = fields.Datetime(
        default=_default_start,
        index=True,
        required=True,
        tracking=True,
        help="Start date of an event, without time for full days events",
    )
    stop = fields.Datetime(
        compute="_compute_stop",
        default=_default_stop,
        store=True,
        readonly=False,
        required=True,
        tracking=True,
        help="Stop date of an event, without time for full days events",
    )
    display_time = fields.Char(
        string="Event Time",
        compute="_compute_display_time",
    )
    allday = fields.Boolean(
        string="All Day",
        default=False,
    )
    start_date = fields.Date(
        compute="_compute_dates",
        inverse="_inverse_dates",
        store=True,
        tracking=True,
    )
    stop_date = fields.Date(
        string="End Date",
        compute="_compute_dates",
        inverse="_inverse_dates",
        store=True,
        tracking=True,
    )
    duration = fields.Float(
        compute="_compute_duration",
        store=True,
        readonly=False,
    )
    # linked document
    res_id = fields.Many2oneReference(
        model_field="res_model",
        string="Document ID",
    )
    res_model_id = fields.Many2one(
        comodel_name="ir.model",
        string="Document Model",
        ondelete="cascade",
    )
    res_model = fields.Char(
        related="res_model_id.model",
        string="Document Model Name",
        readonly=True,
    )
    res_model_name = fields.Char(related="res_model_id.name")
    # messaging
    activity_ids = fields.One2many(
        comodel_name="mail.activity",
        inverse_name="calendar_event_id",
        string="Activities",
    )
    # attendees
    attendee_ids = fields.One2many(
        comodel_name="calendar.attendee",
        inverse_name="event_id",
        string="Participant",
    )
    current_attendee = fields.Many2one(
        comodel_name="calendar.attendee",
        compute="_compute_current_attendee",
        search="_search_current_attendee",
    )
    current_status = fields.Selection(
        related="current_attendee.state",
        string="Attending?",
        readonly=False,
    )
    should_show_status = fields.Boolean(compute="_compute_should_show_status")
    # `active_test` off because `partner_ids` and `attendee_ids` are two views of
    # one set and the model relies on it: `_attendees_values` reads
    # `self.partner_ids` as the attendees a record currently has, and derives the
    # create/unlink commands for `calendar.attendee` from the difference against
    # what the caller asked for. `calendar.attendee` has no `active` column, so
    # with the comodel's active test left on, an archived partner sat in the
    # relation table and in `attendee_ids` while reading `partner_ids` back
    # denied they were there: they could never be removed (never in
    # `removed_partner_ids`) and were re-added as a second attendee by the next
    # write that named them (always in `added_partner_ids`).
    partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="calendar_event_res_partner_rel",
        string="Attendees",
        default=_default_partner_ids,
        context={"active_test": False},
    )
    invalid_email_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        compute="_compute_invalid_email_partner_ids",
    )
    unavailable_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        string="Unavailable Attendees",
        compute="_compute_unavailable_partner_ids",
    )
    # alarms
    alarm_ids = fields.Many2many(
        comodel_name="calendar.alarm",
        relation="calendar_alarm_calendar_event_rel",
        string="Reminders",
        ondelete="restrict",
        help="Notifications sent to all attendees to remind of the meeting.",
    )
    # RECURRENCE FIELD
    recurrency = fields.Boolean(string="Recurrent")
    recurrence_id = fields.Many2one(
        comodel_name="calendar.recurrence",
        string="Recurrence Rule",
        index="btree_not_null",
    )
    follow_recurrence = fields.Boolean(default=False)  # Indicates if an event follows the recurrence, i.e. is not an exception
    recurrence_update = fields.Selection(
        selection=[
            ("this", "This event"),
            ("subsequent", "This and following events"),
            ("all", "All events"),
        ],
        help="Choose what to do with other events in the recurrence. Updating All Events is not allowed when dates or time is modified",
    )
    # Those field are pseudo-related fields of recurrence_id.
    # They can't be "real" related fields because it should work at record creation
    # when recurrence_id is not created yet.
    # If some of these fields are set and recurrence_id does not exists,
    # a `calendar.recurrence.rule` will be dynamically created.
    rrule = fields.Char(
        string="Recurrent Rule",
        compute="_compute_recurrence",
        readonly=False,
    )
    repeat_unit_ui = fields.Selection(
        selection=REPEAT_UNIT_SELECTION_UI,
        string="Repeat",
        compute="_compute_repeat_unit_ui",
        readonly=False,
        help="Let the event automatically repeat at that interval",
    )
    repeat_unit = fields.Selection(
        selection=REPEAT_UNIT_SELECTION,
        string="Recurrence",
        compute="_compute_recurrence",
        readonly=False,
        help="Let the event automatically repeat at that interval",
    )
    event_tz = fields.Selection(
        selection=_selection_timezones,
        string="Timezone",
        compute="_compute_recurrence",
        readonly=False,
    )
    repeat_type = fields.Selection(
        selection=REPEAT_TYPE_SELECTION_RRULE,
        string="Recurrence Termination",
        compute="_compute_recurrence",
        readonly=False,
    )
    repeat_interval = fields.Integer(
        string="Repeat On",
        compute="_compute_recurrence",
        readonly=False,
        help="Repeat every (Days/Week/Month/Year)",
    )
    repeat_number = fields.Integer(
        string="Number of Repetitions",
        compute="_compute_recurrence",
        readonly=False,
        help="Repeat x times",
    )
    mon = fields.Boolean(
        compute="_compute_recurrence",
        readonly=False,
    )
    tue = fields.Boolean(
        compute="_compute_recurrence",
        readonly=False,
    )
    wed = fields.Boolean(
        compute="_compute_recurrence",
        readonly=False,
    )
    thu = fields.Boolean(
        compute="_compute_recurrence",
        readonly=False,
    )
    fri = fields.Boolean(
        compute="_compute_recurrence",
        readonly=False,
    )
    sat = fields.Boolean(
        compute="_compute_recurrence",
        readonly=False,
    )
    sun = fields.Boolean(
        compute="_compute_recurrence",
        readonly=False,
    )
    month_by = fields.Selection(
        selection=MONTH_BY_SELECTION,
        string="Option",
        compute="_compute_recurrence",
        readonly=False,
    )
    day = fields.Integer(
        string="Date of month",
        compute="_compute_recurrence",
        readonly=False,
    )
    weekday = fields.Selection(
        selection=WEEKDAY_SELECTION,
        compute="_compute_recurrence",
        readonly=False,
    )
    byday = fields.Selection(
        selection=BYDAY_SELECTION,
        string="By day",
        compute="_compute_recurrence",
        readonly=False,
    )
    repeat_until = fields.Date(
        compute="_compute_recurrence",
        readonly=False,
    )
    # UI Fields.
    display_description = fields.Boolean(compute="_compute_display_description")
    attendees_count = fields.Integer(compute="_compute_attendees_count")
    accepted_count = fields.Integer(compute="_compute_attendees_count")
    declined_count = fields.Integer(compute="_compute_attendees_count")
    tentative_count = fields.Integer(compute="_compute_attendees_count")
    awaiting_count = fields.Integer(compute="_compute_attendees_count")
    user_can_edit = fields.Boolean(compute="_compute_user_can_edit")

    @api.depends("attendee_ids")
    @api.depends_context("uid")
    def _compute_should_show_status(self):
        for event in self:
            event.should_show_status = event.current_attendee and any(
                attendee.partner_id != self.env.user.partner_id
                for attendee in event.attendee_ids
            )

    # `attendee_ids.state` was a dependency here and is not one: this selects an
    # attendee by `partner_id` and never reads a state, so every RSVP in the
    # database invalidated it -- and `should_show_status` with it -- for nothing.
    # `current_status` is a *related* on `current_attendee.state` and invalidates
    # itself.
    @api.depends("attendee_ids", "attendee_ids.partner_id")
    @api.depends_context("uid")
    def _compute_current_attendee(self):
        for event in self:
            current_attendee = event.attendee_ids.filtered(
                lambda attendee: attendee.partner_id == self.env.user.partner_id
            )
            event.current_attendee = current_attendee and current_attendee[0]

    def _search_current_attendee(self, operator, value):
        return [
            (
                "attendee_ids",
                "any",
                [
                    ("partner_id", "=", self.env.user.partner_id.id),
                    ("id", operator, value),
                ],
            )
        ]

    @api.depends("attendee_ids", "attendee_ids.state", "partner_ids")
    def _compute_attendees_count(self):
        for event in self:
            count_event = Counter(event.attendee_ids.mapped("state"))
            event.update(
                {
                    "accepted_count": count_event["accepted"],
                    "declined_count": count_event["declined"],
                    "tentative_count": count_event["tentative"],
                    # All five come from `attendee_ids`, so the headline and
                    # the breakdown cannot contradict each other. The headline
                    # used to be `len(partner_ids)`, and a many2many read drops
                    # archived records while the attendee rows survive: archive
                    # a contact who is on a meeting and the event reads "0
                    # guests, 1 accepted". `attendee_ids` is the authoritative
                    # invitation list -- an attendee whose contact was
                    # deactivated is still invited, and theirs is still the row
                    # carrying the answer.
                    #
                    # `awaiting` stays a count of the unanswered rather than the
                    # total minus the answers: that subtraction went negative
                    # whenever the two sources disagreed, which this makes
                    # impossible rather than merely survivable.
                    "attendees_count": len(event.attendee_ids),
                    "awaiting_count": count_event["needsAction"],
                }
            )

    @api.depends("partner_ids")
    @api.depends_context("uid")
    def _compute_user_can_edit(self):
        for event in self:
            # By default, only current attendees and the organizer can edit the event.
            editor_candidates = set(event.partner_ids.user_ids + event.user_id)
            # Right before saving the event, old partners must be able to save changes.
            if event._origin:
                editor_candidates |= set(event._origin.partner_ids.user_ids)
            # Non-private events must be editable by uninvited administrators.
            if (
                self.env.user.has_group("base.group_system")
                and event.privacy != "private"
            ):
                editor_candidates.add(self.env.user)
            event.user_can_edit = self.env.user in editor_candidates

    @api.depends("partner_ids")
    def _compute_invalid_email_partner_ids(self):
        for event in self:
            event.invalid_email_partner_ids = event.partner_ids.filtered(
                lambda a: not (a.email and single_email_re.match(a.email))
            )

    @api.depends("privacy", "user_id")
    def _compute_effective_privacy(self):
        for event in self:
            event.effective_privacy = (
                event.privacy or event.sudo().user_id.calendar_default_privacy
            )

    @api.depends_context("active_model", "active_id")
    def _compute_is_highlighted(self):
        if self.env.context.get("active_model") == "res.partner":
            partner_id = self.env.context.get("active_id")
            for event in self:
                if event.partner_ids.filtered(lambda s: s.id == partner_id):
                    event.is_highlighted = True
                else:
                    event.is_highlighted = False
        else:
            for event in self:
                event.is_highlighted = False

    @api.depends("partner_id", "attendee_ids")
    def _compute_is_organizer_alone(self):
        """
        Check if the organizer of the event is the only one who has accepted the event.
        It does not apply if the organizer is the only attendee of the event because it
        would represent a personnal event.
        The goal of this field is to highlight to the user that the others attendees are
        not available for this event.
        """
        for event in self:
            organizer = event.attendee_ids.filtered(
                lambda a: a.partner_id == event.partner_id  # noqa: B023 - filtered() is invoked eagerly within this same loop iteration, not deferred
            )
            all_declined = not any(
                (event.attendee_ids - organizer).filtered(
                    lambda a: a.state != "declined"
                )
            )
            event.is_organizer_alone = len(event.attendee_ids) > 1 and all_declined

    def _compute_display_time(self):
        for meeting in self:
            meeting.display_time = self._get_display_time(
                meeting.start, meeting.stop, meeting.duration, meeting.allday
            )

    @api.depends("allday", "start", "stop")
    def _compute_dates(self):
        """Adapt the value of start_date(time)/stop_date(time)
        according to start/stop fields and allday.
        """
        for meeting in self:
            if meeting.allday and meeting.start and meeting.stop:
                meeting.start_date = meeting.start.date()
                meeting.stop_date = meeting.stop.date()
            else:
                meeting.start_date = False
                meeting.stop_date = False

    @api.depends("stop", "start")
    def _compute_duration(self):
        for event in self:
            event.duration = self._get_duration(event.start, event.stop)

    @api.depends("start", "duration")
    def _compute_stop(self):
        # stop and duration fields both depends on the start field.
        # But they also depends on each other.
        # When start is updated, we want to update the stop datetime based on
        # the *current* duration. We want: change start => keep the duration fixed and
        # recompute stop accordingly.
        # However, while computing stop, duration is marked to be recomputed. Calling `event.duration` would trigger
        # its recomputation. To avoid this we manually mark the field as computed.
        duration_field = self._fields["duration"]
        self.env.remove_to_compute(duration_field, self)
        for event in self:
            # Round the duration (in hours) to the minute to avoid weird situations where the event
            # stops at 4:19:59, later displayed as 4:19.
            event.stop = event.start and event.start + timedelta(
                minutes=round((event.duration or 1.0) * 60)
            )
            if event.allday:
                event.stop -= timedelta(seconds=1)

    @api.onchange("start_date", "stop_date")
    def _onchange_date(self):
        """This onchange is required for cases where the stop/start is False and we set an allday event.
        The inverse method is not called in this case because start_date/stop_date are not used in any
        compute/related, so we need an onchange to set the start/stop values in the form view
        """
        for event in self:
            if event.stop_date and event.start_date:
                event.with_context(is_calendar_event_new=True).write(
                    {
                        "start": fields.Datetime.from_string(event.start_date).replace(
                            hour=8
                        ),
                        "stop": fields.Datetime.from_string(event.stop_date).replace(
                            hour=18
                        ),
                    }
                )

    def _inverse_dates(self):
        """This method is used to set the start and stop values of all day events.
        The calendar view needs date_start and date_stop values to display correctly the allday events across
        several days. As the user edit the {start,stop}_date fields when allday is true,
        this inverse method is needed to update the  start/stop value and have a relevant calendar view.
        """
        for meeting in self:
            if meeting.allday:
                # Convention break:
                # stop and start are NOT in UTC in allday event
                # in this case, they actually represent a date
                # because fullcalendar just drops times for full day events.
                # i.e. Christmas is on 25/12 for everyone
                # even if people don't celebrate it simultaneously
                enddate = fields.Datetime.from_string(meeting.stop_date or meeting.stop)
                enddate = enddate.replace(hour=18)

                startdate = fields.Datetime.from_string(
                    meeting.start_date or meeting.start
                )
                startdate = startdate.replace(hour=8)  # Set 8 AM

                if meeting.start_date and meeting.stop_date:
                    # If start_date or stop_date is set, use start_date and stop_date;
                    # otherwise, use start and stop.
                    meeting.write(
                        {
                            "start": startdate.replace(tzinfo=None),
                            "stop": enddate.replace(tzinfo=None),
                        }
                    )
                else:
                    meeting.write(
                        {
                            "start_date": startdate.replace(tzinfo=None),
                            "stop_date": enddate.replace(tzinfo=None),
                        }
                    )

    @api.constrains("start", "stop", "start_date", "stop_date")
    def _check_closing_date(self):
        for meeting in self:
            if (
                not meeting.allday
                and meeting.start
                and meeting.stop
                and meeting.stop < meeting.start
            ):
                raise ValidationError(
                    _(
                        "The ending date and time cannot be earlier than the starting date and time.\n"
                        "Meeting “%(name)s” starts at %(start_time)s and ends at %(end_time)s",
                        name=meeting.name,
                        start_time=meeting.start,
                        end_time=meeting.stop,
                    ),
                )
            if (
                meeting.allday
                and meeting.start_date
                and meeting.stop_date
                and meeting.stop_date < meeting.start_date
            ):
                raise ValidationError(
                    _(
                        "The ending date cannot be earlier than the starting date.\n"
                        "Meeting “%(name)s” starts on %(start_date)s and ends on %(end_date)s",
                        name=meeting.name,
                        start_date=meeting.start_date,
                        end_date=meeting.stop_date,
                    ),
                )

    def _get_organizer_validation_conditions(self, vals_list):
        """Method for check in the microsoft_calendar module that needs to be
        overridden in appointment.
        """
        return [True] * len(vals_list)

    @api.depends("recurrence_id", "recurrency")
    def _compute_repeat_unit_ui(self):
        defaults = self.env["calendar.recurrence"].default_get(
            ["repeat_interval", "repeat_unit"]
        )
        for event in self:
            if event.recurrency:
                if event.recurrence_id:
                    event.repeat_unit_ui = (
                        "custom"
                        if event.recurrence_id.repeat_interval != 1
                        else (event.recurrence_id.repeat_unit)
                    )
                else:
                    event.repeat_unit_ui = defaults["repeat_unit"]

    @api.depends("recurrence_id", "recurrency", "repeat_unit_ui")
    def _compute_recurrence(self):
        recurrence_fields = self._get_fields_recurrent()
        false_values = dict.fromkeys(
            recurrence_fields, False
        )  # computes need to set a value
        defaults = self.env["calendar.recurrence"].default_get(recurrence_fields)
        default_rrule_values = self.recurrence_id.default_get(recurrence_fields)
        for event in self:
            if event.recurrency:
                current_rrule = (
                    event.repeat_unit
                    if event.repeat_unit_ui == "custom"
                    else event.repeat_unit_ui
                )
                event.update(
                    defaults
                )  # default recurrence values are needed to correctly compute the recurrence params
                event_values = event._get_recurrence_params()
                rrule_values = {
                    field: event.recurrence_id[field]
                    for field in recurrence_fields
                    if event.recurrence_id[field]
                }
                rrule_values = rrule_values or default_rrule_values
                rrule_values["repeat_unit"] = (
                    current_rrule
                    or rrule_values.get("repeat_unit")
                    or defaults["repeat_unit"]
                )
                event.update(
                    {**false_values, **defaults, **event_values, **rrule_values}
                )
            else:
                event.update(false_values)

    @api.depends("description")
    def _compute_display_description(self):
        for event in self:
            event.display_description = not is_html_empty(event.description)

    @api.depends(
        "partner_ids",
        "start",
        "stop",
        "allday",
        "start_date",
        "stop_date",
        "attendee_ids.state",
    )
    def _compute_unavailable_partner_ids(self):
        self.unavailable_partner_ids = False
        windows = [
            (start, stop, event, partner)
            for event in self.filtered(lambda event: event.start and event.stop)
            for partner in event.partner_ids
            for start, stop in event._get_attendee_intervals(partner)
        ]
        if not windows:
            return
        # Keep one candidate search for the batch; the hook must receive only
        # events overlapping this attendee's actual window.
        busy_events = self.partner_ids._search_busy_calendar_events(
            min(start for start, _stop, _event, _partner in windows),
            max(stop for _start, stop, _event, _partner in windows),
        )
        for start, stop, event, partner in windows:
            events_by_partner = partner._group_busy_calendar_events(
                busy_events, start, stop
            )
            if event._is_partner_unavailable(
                partner,
                events_by_partner.get(partner._origin.id, self.env["calendar.event"]),
            ):
                event.unavailable_partner_ids |= partner

    # A deliberate cycle, measured rather than assumed: `videocall_location` is
    # stored and computed from `videocall_source`, which is computed from
    # `videocall_location`. It terminates because the compute assigns only for
    # `source == "discuss"` and then writes the URL its own token implies.
    #
    # Depending on `videocall_source` changes exactly ONE case out of the five
    # this was measured against, and it is not the one you would guess. It is
    # *not* what gives each occurrence of a recurrence its own room -- remove
    # the dependency and three occurrences still get three distinct tokens,
    # because `access_token` is `copy=False` and the create path mints one. The
    # single case it decides is **writing a discuss-shaped URL onto an event
    # that has no token**: with the dependency a token is minted and the URL
    # repointed at it, without it the token stays False and the URL names a
    # token no event has -- `/calendar/join_videocall` resolves
    # `('access_token', '=', token)`, so that link is permanently dead. The
    # regeneration is self-healing, not a value being trampled.
    @api.depends("videocall_source", "access_token")
    def _compute_videocall_location(self):
        for event in self:
            if event.videocall_source == "discuss":
                event._set_discuss_videocall_location()

    def _is_partner_unavailable(self, partner, partner_events):
        self.check_singleton()
        return any(
            intervals_overlap(own_interval, other_interval)
            for own_interval in self._get_attendee_intervals(partner)
            for partner_event in partner_events
            if partner_event != self
            for other_interval in partner_event._get_attendee_intervals(partner)
        )

    @api.model
    def _set_videocall_location(self, vals_list):
        for vals in vals_list:
            if not vals.get("videocall_location"):
                continue
            url = urlsplit(vals["videocall_location"])
            if url.scheme in ("http", "https"):
                continue
            # relative url to convert to absolute
            base = urlsplit(self.get_base_url())
            vals["videocall_location"] = urlunsplit(
                url._replace(scheme=base.scheme, netloc=base.netloc)
            )

    def _is_video_call_required(self):
        # The hook the calendar sync providers and time off answer: whether
        # this event wants a video call created for it.
        self.check_singleton()
        return True

    @api.depends("videocall_location")
    def _compute_videocall_source(self):
        for event in self:
            if (
                event.videocall_location
                and self.DISCUSS_ROUTE in event.videocall_location
            ):
                event.videocall_source = "discuss"
            else:
                event.videocall_source = "custom"

    def _set_discuss_videocall_location(self):
        """
        This method sets the videocall_location to a discuss route.
        If no access_token exists for this event, we create one.
        Recurring events will have different access_tokens.
        This is done by design to prevent users not being able to join a discuss meeting because the base event of the recurrency was deleted.
        """
        if not self.access_token:
            self.access_token = generate_calendar_token()
        self.videocall_location = (
            f"{self.get_base_url()}/{self.DISCUSS_ROUTE}/{self.access_token}"
        )

    @api.model
    def get_discuss_videocall_location(self):
        access_token = generate_calendar_token()
        return f"{self.get_base_url()}/{self.DISCUSS_ROUTE}/{access_token}"

    # ------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------

    # Values `create` needs present on every vals dict, whether or not the
    # caller supplied them: the activity and contact-description steps below
    # read them unconditionally.
    _CREATE_DEFAULT_FNAMES = (
        "activity_ids",
        "allday",
        "description",
        "name",
        "partner_ids",
        "res_model_id",
        "res_id",
        "start",
        "user_id",
    )

    def _create_apply_defaults(self, vals_list, defaults):
        """Fill in `_CREATE_DEFAULT_FNAMES` from `defaults` where absent.

        `res_model` is not among them and is not filled here: it is a stored
        related on `res_model_id.model`, so the ORM derives it from the
        `res_model_id` this does fill. It used to be written too, from a key
        `default_get` is never asked for, which put `None` into every vals dict
        for the ORM to discard.
        """
        # Else bug with quick_create when we are filter on an other user
        return [
            {
                **vals,
                "activity_ids": vals.get("activity_ids", defaults.get("activity_ids")),
                "allday": vals.get("allday", defaults.get("allday")),
                "description": vals.get("description", defaults.get("description")),
                "name": vals.get("name", defaults.get("name")),
                # when res_id is not defined or vals['res_id'] == 0, fallback on default
                "res_id": vals.get("res_id") or defaults.get("res_id"),
                "res_model_id": vals.get("res_model_id", defaults.get("res_model_id")),
                "start": vals.get("start", defaults.get("start")),
                "user_id": vals.get(
                    "user_id", defaults.get("user_id", self.env.user.id)
                ),
            }
            for vals in vals_list
        ]

    def _create_prepare_stop(self, vals_list):
        pending = [
            vals for vals in vals_list if "stop" not in vals and vals.get("start")
        ]
        if not pending or "default_stop" in self.env.context:
            return
        default_duration = (
            self.env.context.get("default_duration") or self.get_default_duration()
        )
        for vals in pending:
            duration = vals.get("duration") or default_duration
            stop = fields.Datetime.to_datetime(vals["start"]) + timedelta(
                minutes=round(duration * 60)
            )
            vals["stop"] = stop - timedelta(seconds=1) if vals.get("allday") else stop

    @api.model_create_multi
    def create(self, vals_list):
        # Prevent sending update notification when _inverse_dates is called
        self = self.with_context(is_calendar_event_new=True)
        defaults = self.browse().default_get(list(self._CREATE_DEFAULT_FNAMES))
        vals_list = self._create_apply_defaults(vals_list, defaults)
        self._create_prepare_stop(vals_list)
        self._create_prepare_activities(vals_list)
        self._set_videocall_location(vals_list)
        vals_list = self._create_prepare_attendees(vals_list, defaults)
        if not self.env.context.get("skip_contact_description"):
            self._create_prepare_contact_description(vals_list)

        events = self._create_split_by_recurrency(vals_list)

        events.filtered(
            lambda event: event.start > fields.Datetime.now()
        ).attendee_ids._send_invitation_emails()
        self._create_sync_activities(events, vals_list)
        if not self.env.context.get("dont_notify"):
            self._create_setup_alarms(events, vals_list)
        # `_reservation_sync_manual`: project once this model is done with the
        # records.  `_create_split_by_recurrency` may have expanded one vals
        # dict into a whole series, so `events` is the authoritative set.
        to_sync = events._active_for_sync()
        to_sync.flush_recordset()
        to_sync._sync_reservations()
        return events.with_context(is_calendar_event_new=False)

    def _create_prepare_activities(self, vals_list):
        """Attach a meeting activity to the linked document, in place.

        An event created *from* a record (a lead, an order) that supports
        activities gets one, so the document shows the meeting in its activity
        stream. Skipped when the caller already supplied a complete
        `(0, 0, vals)` activity command, unless the event is being created from
        an activity that already has an event -- then a second one is wanted.
        """
        meeting_activity_types = self.env["mail.activity.type"].search(
            [("category", "=", "meeting")]
        )
        if not meeting_activity_types:
            return
        # get list of models ids and filter out None values directly
        model_ids = list(filter(None, {values["res_model_id"] for values in vals_list}))
        all_models = self.env["ir.model"].sudo().browse(model_ids)
        # TDE FIXME: clean that method, be more values-based
        excluded_models = self._get_activity_excluded_models()

        # if user is creating an event for an activity that already has one, create a second activity
        existing_event, existing_type = self.browse(), self.env["mail.activity.type"]
        orig_activity_ids = self.env["mail.activity"].browse(
            self.env.context.get("orig_activity_ids", [])
        )

        if len(orig_activity_ids) == 1:
            existing_event = orig_activity_ids.calendar_event_id
            if (
                existing_event
                and orig_activity_ids.activity_type_id.category == "meeting"
            ):
                existing_type = orig_activity_ids.activity_type_id

        for values in vals_list:
            # created from calendar: try to create an activity on the related record
            if values["activity_ids"] and not existing_event:
                continue
            res_model = all_models.filtered(
                lambda m: m.id == values["res_model_id"]  # noqa: B023 - filtered() is invoked eagerly within this same loop iteration, not deferred
            )
            res_id = values["res_id"]
            if (
                not res_model
                or not res_id
                or res_model.model in excluded_models
                or not res_model.is_mail_activity
            ):
                continue

            meeting_activity_type = self.env["mail.activity.type"]
            if existing_type and existing_type.res_model in {False, res_model.model}:
                meeting_activity_type = existing_type
            if not meeting_activity_type:
                meeting_activity_type = meeting_activity_types.filtered(
                    lambda act: act.res_model in {False, res_model.model}  # noqa: B023 - filtered() is invoked eagerly within this same loop iteration, not deferred
                )
            if not meeting_activity_type:
                continue

            values["activity_ids"] = [
                (
                    0,
                    0,
                    self._prepare_meeting_activity_vals(
                        values, meeting_activity_type[0]
                    ),
                )
            ]

    def _prepare_meeting_activity_vals(self, values, activity_type):
        """Activity values mirroring the event values it is created from."""
        activity_vals = {
            "res_model_id": values["res_model_id"],
            "res_id": values["res_id"],
            "activity_type_id": activity_type.id,
        }
        if values["description"]:
            activity_vals["note"] = values["description"]
        if values["name"]:
            activity_vals["summary"] = values["name"]
        if values["start"]:
            activity_vals["date_deadline"] = self._get_activity_deadline_from_start(
                fields.Datetime.from_string(values["start"]), values["allday"]
            )
        if values["user_id"]:
            activity_vals["user_id"] = values["user_id"]
        return activity_vals

    def _create_prepare_attendees(self, vals_list, defaults):
        """Derive the attendee commands from the partners, where absent.

        An explicit `attendee_ids` wins (Google and Outlook events arrive with
        one); otherwise the current user is added, which is what makes a
        quick-created event have an organizer.
        """
        default_partners_ids = defaults.get("partner_ids") or (
            [(4, self.env.user.partner_id.id)]
        )
        return [
            dict(
                vals,
                attendee_ids=self._attendees_values(
                    vals.get("partner_ids", default_partners_ids)
                ),
            )
            if not vals.get("attendee_ids")
            else vals
            for vals in vals_list
        ]

    def _create_prepare_contact_description(self, vals_list):
        """Append the organizer's and first attendee's details to the description, in place."""
        organizer_ids, partner_ids = set(), set()
        vals_partner_list = []
        for vals in vals_list:
            if vals.get("user_id"):
                organizer_ids.add(vals["user_id"])
            # attendee_ids structure = [[2, partner_id_to_remove], [0, 0, {'partner_id': partner_id_to_add}], ...]
            partner_ids_from_attendees = {
                attendee_vals[2]["partner_id"]
                for attendee_vals in vals["attendee_ids"]
                if len(attendee_vals) > 2
                and isinstance(attendee_vals[2], dict)
                and "partner_id" in attendee_vals[2]
            }
            partner_ids.update(partner_ids_from_attendees)
            vals_partner_list.append(partner_ids_from_attendees)
        organizers = (
            self.env["res.users"].browse(organizer_ids).with_prefetch(organizer_ids)
        )
        partners = (
            self.env["res.partner"].browse(partner_ids).with_prefetch(partner_ids)
        )

        for vals, vals_partner_ids in zip(vals_list, vals_partner_list, strict=True):
            contact_description = self._get_contact_details_description(
                organizers.browse(vals.get("user_id", False)),
                partners.browse(vals_partner_ids),
            )
            if not is_html_empty(contact_description):
                base_description = (
                    f"{vals['description']}<br/>"
                    if not is_html_empty(vals.get("description"))
                    else ""
                )
                vals["description"] = (
                    f"<div>{base_description}{contact_description}</div>"
                )

    def _create_split_by_recurrency(self, vals_list):
        """Create the events and return them in `vals_list` order.

        Recurring and non-recurring vals go through two separate super() calls
        (recurring events need follow_recurrence=True and a recurrence applied
        afterwards). The returned recordset must still line up with `vals_list`:
        the callers pair each event with its own vals by position. Track the
        original index of every vals so `events` can be rebuilt in caller order.
        """
        recurrence_fields = self._get_fields_recurrent()
        other_idx = [
            i for i, vals in enumerate(vals_list) if not vals.get("recurrency")
        ]
        recurring_idx = [
            i for i, vals in enumerate(vals_list) if vals.get("recurrency")
        ]
        other_vals = [vals_list[i] for i in other_idx]
        recurring_vals = [vals_list[i] for i in recurring_idx]

        other_events = super().create(other_vals)

        for vals in recurring_vals:
            vals["follow_recurrence"] = True
        recurring_events = super().create(recurring_vals)

        events_by_index = dict(zip(other_idx, other_events, strict=True))
        events_by_index.update(zip(recurring_idx, recurring_events, strict=True))
        events = self.browse(events_by_index[i].id for i in range(len(vals_list)))

        for event, vals in zip(recurring_events, recurring_vals, strict=True):
            recurrence_values = {
                field: vals.pop(field) for field in recurrence_fields if field in vals
            }
            if vals.get("recurrency"):
                detached_events = event.with_context(
                    skip_contact_description=True
                )._apply_recurrence_values(recurrence_values)
                detached_events.active = False

        return events

    @api.model
    def _create_sync_activities(self, events, vals_list):
        """Push the event values onto activities the caller did not fully specify.

        Heuristic, unchanged: a new `(0, 0, vals)` command is considered
        complete, so only events whose activity commands include something else
        are synced. `events` is in `vals_list` order, so this pairing is correct.
        """
        to_sync_activities = self.browse()
        for event, event_values in zip(events, vals_list, strict=True):
            if any(
                command[0] != 0 for command in event_values.get("activity_ids") or []
            ):
                to_sync_activities += event
        to_sync_activities._sync_activities(
            fields={f for vals in vals_list for f in vals}
        )

    @api.model
    def _create_setup_alarms(self, events, vals_list):
        """Schedule the cron triggers for the events just created."""
        alarm_events = self.browse()
        for event, values in zip(events, vals_list, strict=True):
            if values.get("allday"):
                # All day events will trigger the _inverse_date method which will create the trigger.
                continue
            alarm_events |= event
        recurring_events = alarm_events.filtered("recurrence_id")
        recurring_events.recurrence_id._schedule_next_occurrence_alarm()
        (alarm_events - recurring_events)._setup_alarms()

    def _compute_field_value(self, field, validate=True):
        if field.compute_sudo:
            return super(
                CalendarEvent, self.with_context(prefetch_fields=False)
            )._compute_field_value(field, validate=validate)
        return super()._compute_field_value(field, validate=validate)

    def _fetch_query(self, query, fields):
        if self.env.su:
            return super()._fetch_query(query, fields)

        public_fnames = self._get_fields_public()
        private_fields = [field for field in fields if field.name not in public_fnames]
        if not private_fields:
            return super()._fetch_query(query, fields)

        fields_to_fetch = list(fields) + [
            self._fields[name] for name in ("privacy", "user_id", "partner_ids")
        ]
        events = super()._fetch_query(query, fields_to_fetch)

        # determine private events to which the user does not participate
        others_private_events = events.filtered(
            lambda ev: ev._check_private_event_conditions()
        )
        if not others_private_events:
            return events

        private_fields.append(self._fields["partner_ids"])
        for field in private_fields:
            replacement = field.convert_to_cache(
                _("Busy") if field.name == "name" else False, others_private_events
            )
            self.env.cache.update(others_private_events, field, repeat(replacement))

        return events

    # ------------------------------------------------------------------
    # Resource reservation integration (contracts from mixin.resource.scheduling)
    # ------------------------------------------------------------------

    def _get_fields_reservation_date(self):
        """Return (start_field, end_field) names for reservation sync."""
        return ("start", "stop")

    def _prepare_reservation_vals_list(self):
        """Project busy, non-declined attendance, once per physical resource."""
        self.check_singleton()
        if not self.start or not self.stop or self.show_as != "busy":
            return []

        vals_list = []
        booked = set()
        partners = self._get_scheduled_partners()
        partner_resources = partners._get_calendar_event_resources()
        for partner in partners:
            resource = partner_resources[partner]
            # One row per resource, not per attendee.  A person invited both in
            # person and through a contact that shares their resource attends the
            # meeting once; the ledger permits repeated resources (a task can book
            # one twice) and would take the duplicates at face value as 200% of
            # that person's capacity, conflicting with themselves.
            if not resource or resource.id in booked:
                continue
            booked.add(resource.id)
            start, stop = self._get_reservation_interval(partner.tz or resource.tz)
            vals_list.append(
                {
                    "name": self.display_name,
                    "date_start": start,
                    "date_end": stop,
                    "resource_id": resource.id,
                    # A meeting takes the attendee whole; there is no notion of
                    # attending a fraction of one.
                    "allocated_percentage": 100.0,
                    "enforcement_mode": "soft",
                }
            )
        return vals_list

    def _get_scheduled_partners(self):
        """Partners whose attendance occupies their personal schedule."""
        self.check_singleton()
        return (
            self.partner_ids
            - self.attendee_ids.filtered(
                lambda attendee: attendee.state == "declined"
            ).partner_id
        )

    def _get_attendee_intervals(self, partner, *, resources=None):
        """Return UTC occupancy for an attendee, excluding a declined invitation.

        All-day meetings use the attendee's civil dates. Availability callers
        can supply resources resolved for the entire batch.
        """
        self.check_singleton()
        if partner not in self._get_scheduled_partners():
            return []
        if not self.allday:
            return [self._get_reservation_interval("UTC")]
        if resources is None:
            resources = partner._get_calendar_event_resources()[partner]
        timezones = {partner.tz or resource.tz or "UTC" for resource in resources}
        return [
            self._get_reservation_interval(timezone)
            for timezone in sorted(timezones or {partner.tz or "UTC"})
        ]

    def _get_reservation_interval(self, tz):
        """Translate all-day civil dates, never their 08:00-18:00 placeholders."""
        self.check_singleton()
        if not self.allday:
            return self.start, self.stop
        zone = timezone(tz or "UTC")
        start = datetime.combine(self.start_date or self.start.date(), time.min, zone)
        stop = datetime.combine(
            (self.stop_date or self.stop.date()) + timedelta(days=1), time.min, zone
        )
        return (
            start.astimezone(UTC).replace(tzinfo=None),
            stop.astimezone(UTC).replace(tzinfo=None),
        )

    def _get_fields_sync_trigger(self):
        """Attendees, title and the busy/free flag also move bookings.

        ``name`` is a trigger because the reservation label is built from
        ``display_name``; ``show_as`` because flipping it to *free* has to
        release the claims, and back to *busy* to retake them.
        """
        return super()._get_fields_sync_trigger() | {
            "partner_ids",
            "name",
            "show_as",
            "allday",
            "start_date",
            "stop_date",
        }

    def _write_recurrence_policy(self, values):
        """Resolve which occurrences this write is meant to touch.

        Consumes `values`' own `recurrence_update` key, which is a UI selection
        rather than a column, and rejects a recurrence edit that no policy
        authorises.

        :rtype: RecurrencePolicy
        """
        setting = values.pop("recurrence_update", None)
        # `recurrence_update` selects which occurrences of an EXISTING recurrence
        # to touch. On an event with no recurrence yet (a plain event being made
        # recurrent), it is meaningless: honouring 'this'/'all' here
        # skipped _apply_recurrence_values and left the record contradictory
        # (recurrency=True, recurrence_id=False), silently dropping the rrule.
        # Its own default is 'this', so this bit any programmatic caller
        # that passed the field through. Treat it as unset so the recurrence is
        # built regardless of which policy was requested.
        if setting and not self.recurrence_id:
            setting = None
        update = bool(
            setting in ("all", "subsequent") and len(self) == 1 and self.recurrence_id
        )
        if any(fname in self._get_fields_recurrent() for fname in values) and not (
            update or values.get("recurrency")
        ):
            raise UserError(_('Unable to save the recurrence with "This Event"'))
        return RecurrencePolicy(
            setting=setting,
            update=update,
            breaking=values.get("recurrency") is False,
            from_base_event=(
                setting == "subsequent" and self == self.recurrence_id.base_event_id
            ),
        )

    def _write_update_recurrence(self, values, recurrence_values, policy):
        """Rewrite the series `policy` selects, consuming the time keys of `values`.

        :return: the event the resulting series is rooted at, and the events
            detached from their recurrence by the rewrite.
        """
        if policy.breaking:
            return self, self._break_recurrence(future=policy.setting == "subsequent")
        time_values = {
            field: values.pop(field)
            for field in self._get_fields_time()
            if field in values
        }
        # prevents copying access_token to other events in recurrency
        values.pop("access_token", None)
        # Both calls return the event the resulting series is rooted at. It is
        # not always ``self``: `_rewrite_recurrence` archives every occurrence
        # and rebuilds from the *base* event, so a write on any other occurrence
        # leaves ``self`` archived and detached, with nobody left to notify.
        if policy.setting == "all" or policy.from_base_event:
            # Update all events: we create a new reccurrence and dismiss the existing events
            return self._rewrite_recurrence(
                values, time_values, recurrence_values
            ), self.browse()
        # Update future events: trim recurrence, delete remaining events except base event and recreate it
        # All the recurrent events processing is done within the following method
        return self._update_future_events(
            values, time_values, recurrence_values
        ), self.browse()

    def _write_sync_reservations(self, written_fnames):
        """Project the write onto the shared reservation ledger.

        `_reservation_sync_manual`: called from the end of `write`, with the
        recurrence rewrite settled. `written_fnames` rather than the values
        dict, which the recurrence branches emptied; `exists()` because
        `_rewrite_recurrence` and `_update_future_events` unlink occurrences,
        `self` among them.
        """
        if not (written_fnames & (self._get_fields_sync_trigger() | {"active"})):
            return
        to_sync = self.exists()._active_for_sync()
        # Settle first: the computes this write triggered are still pending, and
        # reading `stop` to build a booking would otherwise force
        # `_compute_stop` ahead of the inverse that set it.
        to_sync.flush_recordset()
        to_sync._sync_reservations()

    def write(self, values):
        # `_attendees_values` derives the `attendee_ids` commands from
        # `self.partner_ids`, which over a multi-record write is the UNION of
        # every record's attendees. A partner already on one event then counts
        # as present on all of them, so the `(0, 0, …)` that would have added
        # them to the others is never emitted -- and a `Command.SET` that drops
        # a partner only one event had emits an unlink for all. The derivation
        # is only sound when the records agree on who is currently invited, so
        # when they do not, do it one record at a time.
        if "partner_ids" in values and len(self) > 1:
            invited = {tuple(sorted(event.partner_ids.ids)) for event in self}
            if len(invited) > 1:
                for event in self:
                    event.write(dict(values))
                return True

        self = self.with_context(skip_attendee_reservation_sync=True)
        # Snapshot before the pops below: the recurrence branches consume the
        # very keys the sync and the notification decisions need, and
        # ``_rewrite_recurrence`` can archive ``self`` out from under them.
        written_fnames = set(values)
        requested_start = values.get("start")
        previous_attendees = self.attendee_ids
        previous_partners = self.partner_ids
        detached_events = self.env["calendar.event"]
        policy = self._write_recurrence_policy(values)

        # Check the privacy permissions of the events whose organizer is different from the current user.
        self.filtered(
            lambda ev: ev.user_id and self.env.user != ev.user_id
        )._check_calendar_privacy_write_permissions()

        self._write_prepare_values(values)

        touches_time = self._touches_time(values)
        # Alarms are rescheduled when the event moves, when its reminders change,
        # and when its attendees change -- a new attendee has a next-notification
        # of their own, and a removed one no longer has this event's.
        update_alarms = touches_time or "alarm_ids" in values or "partner_ids" in values

        if (
            not policy.setting or policy.setting == "this"
        ) and "follow_recurrence" not in values:
            if touches_time:
                values["follow_recurrence"] = False

        recurrence_values = {
            field: values.pop(field)
            for field in self._get_fields_recurrent()
            if field in values
        }
        notify_from = self
        if policy.update:
            notify_from, detached = self._write_update_recurrence(
                values, recurrence_values, policy
            )
            detached_events |= detached
        else:
            super().write(values)
            self._sync_activities(fields=values.keys())

        # We reapply recurrence for future events and when we add a rrule and 'recurrency' == True on the event
        if (
            policy.setting not in ["this", "all"]
            and not policy.from_base_event
            and not policy.breaking
        ):
            detached_events |= self._apply_recurrence_values(
                recurrence_values, future=policy.setting == "subsequent"
            )

        (detached_events & self).active = False
        (detached_events - self).with_context(archive_on_error=True).unlink()

        if not self.env.context.get("dont_notify") and update_alarms:
            self._write_reschedule_alarms()
        if touches_time:
            self._write_reset_organizer_answer()
        notify_from._write_notify_attendees(
            written_fnames,
            requested_start,
            previous_attendees,
            previous_partners,
            policy.update,
        )

        # Change base event when the main base event is archived. If it isn't done when trying to modify
        # all events of the recurrence an error can be thrown or all the recurrence can be deleted.
        if values.get("active") is False:
            self.env["calendar.recurrence"].search(
                [("base_event_id", "in", self.ids)]
            )._select_new_base_event()

        self._write_sync_reservations(written_fnames)

        return True

    def _write_prepare_values(self, values):
        """Complete `values` in place before it reaches the ORM.

        Two derivations the caller is never asked to make: an absolute videocall
        URL, and the attendee commands that keep `attendee_ids` in step with the
        `partner_ids` being written. Adding somebody to the meeting also adds
        them to its discuss channel, which is a side effect rather than a value,
        and is done here because it needs the same commands.
        """
        self._set_videocall_location([values])
        if "partner_ids" in values:
            values["attendee_ids"] = self._attendees_values(values["partner_ids"])
            self._write_sync_videocall_members(values["partner_ids"])

    def _write_sync_videocall_members(self, partner_commands):
        """Add newly invited partners to the event's discuss channel."""
        if not self.videocall_channel_id:
            return
        new_partner_ids = []
        for command in partner_commands:
            if command[0] == Command.LINK:
                new_partner_ids.append(command[1])
            elif command[0] == Command.SET:
                new_partner_ids.extend(command[2])
        self.videocall_channel_id.add_members(new_partner_ids)

    def _write_reschedule_alarms(self):
        """Reschedule the cron triggers after a write that can move a reminder."""
        self.recurrence_id._schedule_next_occurrence_alarm(recurrence_update=True)
        if not self.recurrence_id:
            self._setup_alarms()

    def _write_reset_organizer_answer(self):
        """Un-accept the organizer when somebody else moved the event.

        Otherwise the base event of a recurrence stays accepted by its organizer
        while the following occurrences are not, which reads as a half-answered
        series.

        Per attendee, against *its own* event's organizer. It used to compare
        every candidate against ``self.user_id.partner_id`` -- a many2one read
        off the whole recordset, so on a multi-record write it is the *union* of
        the organizers' partners, and a union never equals the single partner on
        the left. Moving two events with different organizers in one write
        therefore reset nobody, silently; the single-event case happened to work
        because a one-element union is that one element.
        """
        moved_by_others = self.filtered(
            lambda ev: ev.user_id and ev.user_id != self.env.user
        )
        moved_by_others.attendee_ids.filtered(
            lambda att: att.partner_id == att.event_id.user_id.partner_id
        ).write({"state": "needsAction"})

    def _write_notify_attendees(
        self,
        written_fnames,
        requested_start,
        previous_attendees,
        previous_partners,
        update_recurrence,
    ):
        """Mail the invitation to new attendees and the new date to the old ones.

        `written_fnames` and `requested_start` are `write`'s snapshot of its own
        argument, taken before the recurrence branches empty it. Asking the dict
        meant that a recurrence update -- which pops every time field into
        `time_values` -- reached the "start" test with no "start" left in it and
        returned early, so moving a whole series told nobody the date had
        changed while moving a single occurrence did. That the caller passes
        `update_recurrence` down purely to *un*set
        `calendar_template_ignore_recurrence` shows the branch was meant to be
        reachable.

        An attendee is new only when *both* identities say so: its row is not
        one of `previous_attendees` AND its partner is not one of
        `previous_partners`. Neither test is sufficient alone. Records alone
        break on the "all events" path, which archives every occurrence and
        recreates it, so no attendee row survives the write and everyone looks
        new. Partners alone break because a many2many read drops
        archived records while the attendee rows survive: an attendee whose
        contact was deactivated is absent from `previous_partners`, so a
        partner-only test calls them new and re-invites somebody who was on the
        invitation all along.
        """
        if self.env.context.get("skip_attendee_notification"):
            return
        current_attendees = self.filtered("active").attendee_ids
        previous_partner_ids = set(previous_partners.ids)
        previous_attendee_ids = set(previous_attendees.ids)

        def is_new(attendee):
            return (
                attendee.id not in previous_attendee_ids
                and attendee.partner_id.id not in previous_partner_ids
            )

        if "partner_ids" in written_fnames:
            # we send to all partners and not only the new ones
            current_attendees.filtered(is_new)._notify_attendees(
                self.env.ref(
                    "calendar.calendar_template_meeting_invitation",
                    raise_if_not_found=False,
                ),
                force_send=True,
            )
        # Deliberately narrower than `_touches_time`: an allday event's
        # `start_date`/`stop_date` change gets its own single note-only
        # notification elsewhere (see `test_message_date_changed`), so this
        # email path only cares about the non-allday `start`/`stop` pair --
        # but it must be BOTH, not just `start` (the bug this fixes): a
        # `stop`-only write (event lengthened/shortened, start untouched)
        # used to skip this notification entirely.
        if self.env.context.get("is_calendar_event_new") or not (
            written_fnames & {"start", "stop"}
        ):
            return
        start_date = fields.Datetime.to_datetime(requested_start) or (
            self[:1].start if self else None
        )
        # Only notify on future events
        if start_date and start_date >= fields.Datetime.now():
            current_attendees.filtered(lambda att: not is_new(att)).with_context(
                calendar_template_ignore_recurrence=not update_recurrence
            )._notify_attendees(
                self.env.ref(
                    "calendar.calendar_template_meeting_changedate",
                    raise_if_not_found=False,
                ),
                force_send=True,
            )

    def _check_calendar_privacy_write_permissions(self):
        """
        Checks if current user can write on the events, raising UserError when the event is private.
        We need to manually call the default Access Error because we can't add an access rule for checking
        the calendar defaut privacy of an user from a 'calendar.event' record, since it is a res.users field.
        Otherwise we would have to create a new computed field on that model, which we don't want.
        """
        if not self.env.su:
            for event in self:
                if event._check_private_event_conditions():
                    raise self.env["ir.rule"]._prepare_access_error("write", event)

    def _check_private_event_conditions(self):
        """Checks if the event is private, returning True if the conditions match and False otherwise."""
        self.check_singleton()
        event_is_private = self.privacy == "private"
        calendar_is_private = (
            not self.privacy
            and self.sudo().user_id.calendar_default_privacy == "private"
        )
        user_is_not_partner = (
            self.user_id.id != self.env.uid
            and self.env.user.partner_id not in self.partner_ids
        )
        return (event_is_private or calendar_is_private) and user_is_not_partner

    @api.depends("privacy", "user_id")
    def _compute_display_name(self):
        """Hide private events' name for events which don't belong to the current user."""
        hidden = self.filtered(lambda event: event._check_private_event_conditions())
        hidden.display_name = _("Busy")
        super(CalendarEvent, self - hidden)._compute_display_name()

    def _privacy_restricted_fnames(self, fnames):
        """Return the real, non-public field names among `fnames`.

        A private event is not hidden as a *record* (the employee ir.rule is
        ``[(1, '=', 1)]``); its sensitive *field values* are masked after
        fetching (see `_fetch_query`). Any code path that lets a non-participant
        observe a private field's value some other way — a search domain, an
        ``order``, a group-by, an aggregate — has to be gated too. This is the
        single predicate all of those paths share.

        Only *stored* fields count. Non-field specs (e.g. the ``__count``
        aggregate) carry no field value; and the non-stored computes such as
        ``current_attendee``/``current_status`` resolve through search methods
        that already restrict to the current user, so searching them can never
        expose another user's event and must not drag in the privacy domain.
        Every field `_fetch_query` actually masks is a stored, non-public field,
        so this set is exactly the search/group oracle surface.
        """
        public = self._get_fields_public()
        return {
            fname
            for fname in fnames
            if (field := self._fields.get(fname))
            and field.store
            and fname not in public
        }

    def _search(
        self,
        domain,
        offset=0,
        limit=None,
        order=None,
        *,
        active_test=True,
        bypass_access=False,
    ):
        # A domain and an order are evaluated in SQL against the raw columns,
        # bypassing the field masking `_fetch_query` applies. Without this,
        # `search`/`search_count` are an oracle: a non-participant can recover a
        # private event's name/location/description/attendees character by
        # character. Mirror the guard already applied in `_read_group`.
        if not (self.env.su or bypass_access):
            fnames = self._search_referenced_fnames(domain, order)
            if self._privacy_restricted_fnames(fnames):
                domain = Domain.AND([domain, self._get_domain_default_privacy()])
        return super()._search(
            domain,
            offset=offset,
            limit=limit,
            order=order,
            active_test=active_test,
            bypass_access=bypass_access,
        )

    @api.model
    def _search_referenced_fnames(self, domain, order):
        """Base field names referenced by a search `domain` and `order` string.

        Only the leading segment of a dotted path matters for privacy — it is
        the field on `calendar.event` itself (``partner_ids.user_ids`` →
        ``partner_ids``).
        """
        fnames = {
            condition.field_expr.split(".")[0].split(":")[0]
            for condition in Domain(domain).iter_conditions()
        }
        for spec in (order or "").split(","):
            fname = spec.strip().split(" ")[0].split(".")[0]
            if fname:
                fnames.add(fname)
        return fnames

    @api.model
    def _read_group(
        self,
        domain,
        groupby=(),
        aggregates=(),
        having=(),
        offset=0,
        limit=None,
        order=None,
    ) -> list[tuple]:
        fnames = {
            spec.split(":")[0]
            for spec in itertools.chain(
                groupby,
                aggregates,
                [cond[0] for cond in having if isinstance(cond, (list, tuple))],
            )
        }
        for spec in (order or "").split(","):
            fname = spec.strip().split(" ")[0].split(".")[0].split(":")[0]
            if fname:
                fnames.add(fname)
        if not self.env.su and self._privacy_restricted_fnames(fnames):
            domain = Domain.AND([domain, self._get_domain_default_privacy()])
        return super()._read_group(
            domain,
            groupby,
            aggregates,
            having=having,
            offset=offset,
            limit=limit,
            order=order,
        )

    @api.model
    def _read_grouping_sets(
        self, domain, grouping_sets, aggregates=(), order=None
    ) -> list[tuple]:
        fnames = {
            spec.split(":")[0]
            for spec in itertools.chain(
                *grouping_sets,
                aggregates,
            )
        }
        for spec in (order or "").split(","):
            fname = spec.strip().split(" ")[0].split(".")[0].split(":")[0]
            if fname:
                fnames.add(fname)
        if not self.env.su and self._privacy_restricted_fnames(fnames):
            domain = Domain.AND([domain, self._get_domain_default_privacy()])
        return super()._read_grouping_sets(
            domain, grouping_sets, aggregates, order=order
        )

    def unlink(self):
        if not self:
            return super().unlink()

        # `write()` checks this before mutating; `unlink()` is a mutation too
        # and had no equivalent check, letting anyone who is neither
        # organizer nor attendee delete somebody else's private event.
        self.filtered(
            lambda ev: ev.user_id and self.env.user != ev.user_id
        )._check_calendar_privacy_write_permissions()

        # Get concerned attendees to notify them if there is an alarm on the unlinked events,
        # as it might have changed their next event notification
        events = self.filtered_domain([("alarm_ids", "!=", False)])
        partner_ids = events.mapped("partner_ids").ids

        # don't forget to update recurrences if there are some base events in the set to unlink,
        # but after having removed the events ;-)
        recurrences = self.env["calendar.recurrence"].search(
            [("base_event_id", "in", [e.id for e in self])]
        )

        result = super().unlink()

        if recurrences:
            recurrences._select_new_base_event()

        # Notify the concerned attendees (must be done after removing the events)
        self.env["calendar.alarm_manager"]._notify_next_alarm(partner_ids)
        return result

    def copy(self, default=None):
        """When an event is copied, the attendees should be recreated to avoid sharing the same attendee records
        between copies
        """
        default = dict(default or {})
        # We need to make sure that the attendee_ids are recreated with new ids to avoid sharing attendees between events
        # The copy should not have the same attendee status than the original event
        default.update(partner_ids=[Command.set([])], attendee_ids=[Command.set([])])
        new_events = super(
            CalendarEvent, self.with_context(skip_contact_description=True)
        ).copy(default)
        for old_event, new_event in zip(self, new_events, strict=True):
            new_event.write({"partner_ids": [(Command.set(old_event.partner_ids.ids))]})
        return new_events

    def action_unlink_event(self, recurrence=False):
        """
        Delete the event after displaying the delete wizard if necessary.

        :param recurrence: which occurrences to delete. Accepts the
            `recurrence_update` vocabulary the form view sends
            ('this'/'subsequent'/'all') and the delete wizard's
            own ('one'/'next'/'all'); anything else means this occurrence only.
        :return: Action to delete the event, or to open the wizard
        """
        if self.user_id._has_any_active_synchronization() or len(self.ids) > 1:
            # This branch used to `self.unlink()` and drop `recurrence` on the
            # floor, so a Google- or Outlook-synced user who answered "all
            # events" deleted exactly one occurrence and was redirected as
            # though it had worked. Apply the policy the caller asked for --
            # the same one the wizard applies on the branch below.
            self._unlink_by_recurrence_policy(recurrence)
            return {
                "type": "ir.actions.act_url",
                "target": "self",
                "url": "/odoo/calendar",
            }

        template = self.env.ref(
            "calendar.calendar_template_delete_event", raise_if_not_found=False
        )
        if not template:
            self.unlink()
            _logger.warning(
                'Template "calendar.calendar_template_delete_event" was not found. Cannot send delete notifications.'
            )
            return {}

        if self.ids and (lang := template._render_lang(self.ids)[self.id]):
            # `default_attendee_id` used to be set here from an `attendee_id`
            # parameter that three JS call sites threaded through -- one of them
            # passing a *list* of partner ids. `calendar.popover.delete.wizard`
            # has no `attendee_id` field, so the key was read by nobody.
            context = {
                "default_use_template": bool(template),
                "default_template_id": template.id,
                "default_calendar_event_id": self.id,
                "default_recurrence": recurrence,
                "model_description": self.with_context(lang=lang),
            }
            return {
                "name": _("Delete Event"),
                "res_model": "calendar.popover.delete.wizard",
                "view_id": self.env.ref("calendar.view_event_delete_wizard_form").id,
                "type": "ir.actions.act_window",
                "context": context,
                "target": "new",
                "views": [(False, "form")],
            }
        return None

    def _mail_get_operation_for_mail_message_operation(self, message_operation):
        # reading messages on private events requires write access, not just read access
        private = (
            self.filtered(
                lambda event: (
                    event.privacy == "private"
                    and self.env.user.partner_id not in event.attendee_ids.partner_id
                )
            )
            if message_operation == "read"
            else self.browse()
        )
        result = super(
            CalendarEvent, self - private
        )._mail_get_operation_for_mail_message_operation(message_operation)
        result.update(dict.fromkeys(private, "write"))
        return result

    def _attendees_values(self, partner_commands):
        """
        :param partner_commands: ORM commands for partner_id field (0 and 1 commands not supported)
        :return: associated attendee_ids ORM commands
        """
        attendee_commands = []

        current = set(self.partner_ids.ids)
        desired = set(current)
        if partner_commands and isinstance(partner_commands[0], int):
            partner_commands = [Command.set(partner_commands)]
        for command in partner_commands:
            op = command[0]
            if op in (Command.DELETE, Command.UNLINK):
                desired.discard(command[1])
            elif op == Command.SET:
                desired = set(command[2])
            elif op == Command.LINK:
                desired.add(command[1])
            elif op == Command.CLEAR:
                desired.clear()
        removed_partner_ids = sorted(current - desired)
        added_partner_ids = sorted(desired - current)

        if not self:
            attendees_to_unlink = self.env["calendar.attendee"]
        else:
            attendees_to_unlink = self.env["calendar.attendee"].search(
                [
                    ("event_id", "in", self.ids),
                    ("partner_id", "in", removed_partner_ids),
                ]
            )
        attendee_commands += [
            [2, attendee.id] for attendee in attendees_to_unlink
        ]  # Removes and delete

        attendee_commands += [
            [0, 0, {"partner_id": partner_id}] for partner_id in added_partner_ids
        ]
        return attendee_commands

    def _create_videocall_channel(self):
        if self.recurrency:
            # check if any of the events have videocall_channel_id, if not create one
            event_with_channel = self.env["calendar.event"].search(
                [
                    ("recurrence_id", "=", self.recurrence_id.id),
                    ("videocall_channel_id", "!=", False),
                ],
                limit=1,
            )
            if event_with_channel:
                self.videocall_channel_id = event_with_channel.videocall_channel_id
                return
        self.videocall_channel_id = self._create_videocall_channel_id(
            self.name, self.partner_ids.ids
        )
        self.videocall_channel_id.channel_change_description(
            self.recurrence_id.name if self.recurrency else self.display_time
        )

    def _create_videocall_channel_id(self, name, partner_ids):
        videocall_channel = self.env["discuss.channel"]._create_group(
            partner_ids, default_display_mode="video_full_screen", name=name
        )
        # if recurrent event, set channel to all other records of the same recurrency
        if self.recurrency:
            recurrent_events_without_channel = self.env["calendar.event"].search(
                [
                    ("recurrence_id", "=", self.recurrence_id.id),
                    ("videocall_channel_id", "=", False),
                ]
            )
            recurrent_events_without_channel.videocall_channel_id = videocall_channel
        return videocall_channel

    def _get_domain_default_privacy(self):
        """Search-domain complement of `_check_private_event_conditions`.

        Show an event unless it is private -- explicitly, or by its owner's
        default -- AND the user is neither its organizer nor an attendee. So
        participants (organizer via `user_id`, attendee via `partner_ids`)
        always pass; everyone else passes only for public/confidential events,
        or for default-privacy events whose owner's default is not private.

        :rtype: Domain
        """
        settings = self.env["res.users.settings"].sudo()
        # Owners whose *stored* default is not private ('public'/'confidential').
        owner_default_is_public = Domain(
            "user_id",
            "in",
            settings._search([("calendar_default_privacy", "!=", "private")]).select(
                "user_id"
            ),
        )
        # `_check_private_event_conditions` reads `user_id.calendar_default_privacy`,
        # which falls back to the `calendar.default_privacy` config parameter for a
        # user with no `res.users.settings` row -- OdooBot has none, and neither has
        # anyone who existed before this module was installed. Without the same
        # fallback here the two halves of the pair disagree: the predicate calls such
        # an event public while the domain hides it from everyone, so it vanishes
        # from any search that touches a non-public field even for its own attendees.
        if self.env["res.users"]._get_user_calendar_default_privacy() != "private":
            owner_default_is_public |= Domain(
                "user_id", "not in", settings._search([]).select("user_id")
            )
        return Domain.OR(
            [
                Domain("privacy", "in", ["public", "confidential"]),
                Domain("user_id", "=", self.env.user.id),
                Domain("partner_ids", "in", self.env.user.partner_id.id),
                Domain("privacy", "=", False)
                & (Domain("user_id", "=", False) | owner_default_is_public),
            ]
        )

    def _is_event_over(self):
        """Check if the event is over. This method is used to check if the event
        should trigger invitations with Google Calendar.

        Polymorphic with `calendar.recurrence._is_event_over`; see the note there.

        :return: True if the event is over, False otherwise
        """
        self.check_singleton()
        now = fields.Datetime.now()
        today = fields.Date.today()

        # For all-day events
        if self.allday:
            return self.stop_date and self.stop_date < today

        # For timed events
        return self.stop and self.stop < now

    # ------------------------------------------------------------
    # ACTIONS
    # ------------------------------------------------------------

    # dummy method. this method is intercepted in the frontend and the value is set locally
    def set_discuss_videocall_location(self):
        return True

    # dummy method. this method is intercepted in the frontend and the value is set locally
    def clear_videocall_location(self):
        return True

    def action_view_calendar_event(self):
        if self.res_model and self.res_id:
            return self.env[self.res_model].browse(self.res_id).get_formview_action()
        return False

    def action_sendmail(self):
        if self.env.user.email:
            self.attendee_ids._notify_attendees(
                self.env.ref(
                    "calendar.calendar_template_meeting_invitation",
                    raise_if_not_found=False,
                ),
            )
        return True

    def action_view_composer(self):
        if not self.partner_ids:
            raise UserError(_("There are no attendees on these events"))
        template_id = self.env["ir.model.data"]._xmlid_to_res_id(
            "calendar.calendar_template_meeting_update", raise_if_not_found=False
        )
        # The mail is sent with datetime corresponding to the sending user TZ
        default_composition_mode = self.env.context.get(
            "default_composition_mode",
            self.env.context.get("composition_mode", "comment"),
        )
        compose_ctx = {
            "default_composition_mode": default_composition_mode,
            "default_model": "calendar.event",
            "default_res_ids": self.ids,
            "default_template_id": template_id,
            "default_partner_ids": self.partner_ids.ids,
            "mail_tz": self.env.user.tz,
        }
        return {
            "type": "ir.actions.act_window",
            "name": _("Contact Attendees"),
            "view_mode": "form",
            "res_model": "mail.compose.message",
            "views": [(False, "form")],
            "view_id": False,
            "target": "new",
            "context": compose_ctx,
        }

    def action_join_video_call(self):
        return {
            "type": "ir.actions.act_url",
            "url": self.videocall_location,
            "target": "new",
        }

    def action_join_meeting(self, partner_id):
        """Method used when an existing user wants to join"""
        self.check_singleton()
        partner = self.env["res.partner"].browse(partner_id)
        if partner not in self.partner_ids:
            self.write({"partner_ids": [(4, partner.id)]})

    # The two vocabularies a delete policy arrives in: the form view sends the
    # `recurrence_update` selection, the delete wizard its own `delete` field.
    # They mean the same three things, so normalise once here instead of letting
    # each call site test for one spelling and silently ignore the other. Since
    # `recurrence_update` took the neutral spelling the other models already
    # used, the two now agree on "all" and only the wizard's other two words are
    # still aliases.
    RECURRENCE_DELETE_POLICIES = {
        "all": "all",
        "subsequent": "subsequent",
        "next": "subsequent",
        "this": "this",
        "one": "this",
    }

    @api.model
    def _normalize_recurrence_policy(self, policy):
        """Map either delete vocabulary onto `recurrence_update`'s.

        Anything unrecognised (including False) means this occurrence only: the
        user did ask for a delete, so the one thing we must never do is nothing.
        """
        return self.RECURRENCE_DELETE_POLICIES.get(policy, "this")

    def _unlink_by_recurrence_policy(self, policy):
        """Delete the occurrences `policy` selects, for a possibly-recurrent event."""
        policy = self._normalize_recurrence_policy(policy)
        if policy == "this" or not self.recurrency or len(self) > 1:
            self.unlink()
            return
        self.action_mass_deletion(policy)

    def action_mass_deletion(self, recurrence_update_setting):
        self.check_singleton()
        if recurrence_update_setting == "all":
            events = self.recurrence_id.calendar_event_ids
            self.recurrence_id.unlink()
            events.unlink()
        elif recurrence_update_setting == "subsequent":
            # `_stop_at` does both halves: it detaches the occurrences from this
            # one onward AND trims the rule to end before it. Selecting the rows
            # by hand and unlinking them did only the first, so the recurrence
            # went on claiming its original `count` with no `until`, and the
            # next `_apply_recurrence` -- any later edit of the series reaches
            # one -- recreated every occurrence that had just been deleted.
            # `action_mass_archive`, the sibling this mirrors, already trims.
            self.recurrence_id._stop_at(self).unlink()
        else:
            # Public, RPC-callable method: fail loudly instead of silently
            # no-op'ing on an unrecognized policy. Today's only caller,
            # `_unlink_by_recurrence_policy`, pre-filters 'this' before
            # reaching here, but nothing enforces that for a future caller.
            raise UserError(
                _(
                    "Unknown recurrence update setting: %s",
                    recurrence_update_setting,
                )
            )

    def action_mass_archive(self, recurrence_update_setting):
        """
        The aim of this action purpose is to be called from sync calendar module when mass deletion is not possible.
        """
        self.check_singleton()
        if recurrence_update_setting == "all":
            self.recurrence_id.calendar_event_ids.write(self._prepare_archive_values())
        elif recurrence_update_setting == "subsequent":
            detached_events = self.recurrence_id._stop_at(self)
            detached_events.write(self._prepare_archive_values())
        elif recurrence_update_setting == "this":
            self.write({"active": False, "recurrence_update": "this"})
            if len(self.recurrence_id.calendar_event_ids) == 0:
                self.recurrence_id.unlink()
            elif self == self.recurrence_id.base_event_id:
                self.recurrence_id._select_new_base_event()

    # ------------------------------------------------------------
    # MAILING
    # ------------------------------------------------------------

    def _skip_send_mail_status_update(self):
        """Overridable getter to identify whether to send invitation/cancelation emails."""
        return False

    def _get_mail_tz(self):
        self.check_singleton()
        return self.event_tz or self.env.user.tz

    def _sync_activities(self, fields):
        # update activities
        for event in self:
            if event.activity_ids:
                activity_values = {}
                if "name" in fields:
                    activity_values["summary"] = event.name
                if "description" in fields:
                    activity_values["note"] = event.description
                # protect against loops in case of ill-managed timezones
                if "start" in fields and not self.env.context.get(
                    "mail_activity_meeting_update"
                ):
                    activity_values["date_deadline"] = (
                        self._get_activity_deadline_from_start(
                            event.start, event.allday
                        )
                    )
                if "user_id" in fields:
                    activity_values["user_id"] = event.user_id.id
                if activity_values.keys():
                    # Mirror `mail_activity.write()`'s own loop guard: it sets
                    # `mail_activity_meeting_update` on its outbound write to
                    # us so `_sync_activities` above skips re-deriving
                    # `date_deadline`. Without setting the matching key here,
                    # this write into the activity re-enters
                    # `mail_activity.write()`'s date_deadline sync, which
                    # writes back into this event's `start` -- a redundant
                    # (and, depending on rounding, potentially looping)
                    # round-trip for every plain event.start edit.
                    event.activity_ids.with_context(
                        calendar_event_meeting_update=True
                    ).write(activity_values)

    @api.model
    def _get_activity_deadline_from_start(self, start, allday):
        # self.start is a datetime UTC *only when the event is not allday*
        # activty.date_deadline is a date (No TZ, but should represent the day in which the user's TZ is)
        # See 72254129dbaeae58d0a2055cba4e4a82cde495b7 for the same issue, but elsewhere
        deadline = start
        user_tz = self.env.context.get("tz")
        if user_tz and not allday:
            deadline = deadline.replace(tzinfo=UTC)
            deadline = deadline.astimezone(timezone(user_tz))
        return deadline.date()

    # ------------------------------------------------------------
    # ALARMS
    # ------------------------------------------------------------

    def _get_trigger_alarm_types(self):
        return ["email"]

    def _setup_event_recurrent_alarms(self, events_by_alarm):
        for event in self:
            if event.recurrence_id:
                next_date = event.get_next_alarm_date(events_by_alarm)
                # In cron, setup alarm only when there is a next date on the target. Otherwise the 'now()'
                # check in the call below can generate undeterministic behavior and setup random alarms.
                if next_date:
                    event.recurrence_id.with_context(
                        date=next_date
                    )._schedule_next_occurrence_alarm()

    def _setup_alarms(self):
        """Schedule cron triggers for future events"""
        cron = self.env.ref("calendar.ir_cron_scheduler_alarm").sudo()
        alarm_types = self._get_trigger_alarm_types()
        now = fields.Datetime.now()
        events_to_notify = self.env["calendar.event"]
        triggers_by_events = {}
        for event in self:
            existing_trigger = event.recurrence_id.sudo().trigger_id
            for alarm in (
                alarm for alarm in event.alarm_ids if alarm.alarm_type in alarm_types
            ):
                at = event.start - timedelta(minutes=alarm.duration_minutes)
                create_trigger = not existing_trigger or existing_trigger.call_at != at
                if create_trigger and (not cron.lastcall or at > cron.lastcall):
                    # Don't trigger for past alarms, they would be skipped by design
                    trigger = cron._trigger(at=at)
                    triggers_by_events[event.id] = trigger.id
            if (
                any(alarm.alarm_type == "notification" for alarm in event.alarm_ids)
                and event.stop >= now
            ):
                # notify the attendees through calendar_alarm_manager below
                events_to_notify |= event
        if events_to_notify:
            self.env["calendar.alarm_manager"]._notify_next_alarm(
                events_to_notify.partner_ids.ids
            )
        return triggers_by_events

    def get_next_alarm_date(self, events_by_alarm):
        self.check_singleton()
        now = fields.Datetime.now()
        sorted_alarms = self.alarm_ids.sorted("duration_minutes")
        triggered_alarms = sorted_alarms.filtered(
            # `events_by_alarm[alarm.id]` is the set of events this alarm
            # actually fired for in this cron batch, not just any event -- an
            # alarm shared by several events (a common reminder) is a key in
            # `events_by_alarm` as soon as it fired for ONE of them, so
            # checking only `alarm.id in events_by_alarm` would misread that
            # as "fired for `self`" too.
            lambda alarm: (
                alarm.id in events_by_alarm and self.id in events_by_alarm[alarm.id]
            )
        )[0]
        event_has_future_alarms = sorted_alarms[0] != triggered_alarms
        next_date = None
        if (
            self.recurrence_id.trigger_id
            and self.recurrence_id.trigger_id.call_at <= now
        ):
            next_date = (
                self.start - timedelta(minutes=sorted_alarms[0].duration_minutes)
                if event_has_future_alarms
                else self.start
            )
        # For recurrent events, when there is no next_date and no trigger in the recurence, set the next
        # date as the date of the next event. This keeps the single alarm alive in the recurrence.
        recurrence_has_no_trigger = (
            self.recurrence_id and not self.recurrence_id.trigger_id
        )
        if recurrence_has_no_trigger and not next_date and len(sorted_alarms) > 0:
            future_recurrent_events = self.recurrence_id.calendar_event_ids.filtered(
                lambda ev: ev.start > self.start
            )
            if future_recurrent_events:
                # The next event (minus the alarm duration) will be the next date.
                next_recurrent_event = future_recurrent_events.sorted("start")[0]
                next_date = next_recurrent_event.start - timedelta(
                    minutes=sorted_alarms[0].duration_minutes
                )
        return next_date

    # ------------------------------------------------------------
    # RECURRENCY
    # ------------------------------------------------------------

    def _apply_recurrence_values(self, values, future=True):
        """Apply the new recurrence rules in `values`. Create a recurrence if it does not exist
        and create all missing events according to the rrule.
        If the changes are applied to future
        events only, a new recurrence is created with the updated rrule.

        :param values: new recurrence values to apply
        :param future: rrule values are applied to future events only if True.
                       Rrule changes are applied to all events in the recurrence otherwise.
                       (ignored if no recurrence exists yet).
        :return: events detached from the recurrence
        """
        if not values:
            return self.browse()
        recurrence_vals = []
        to_update = self.env["calendar.recurrence"]
        for event in self:
            if not event.recurrence_id:
                recurrence_vals += [
                    dict(
                        values,
                        base_event_id=event.id,
                        calendar_event_ids=[(4, event.id)],
                    )
                ]
            elif future:
                to_update |= event.recurrence_id._split_from(event, values)
        self.write({"recurrency": True, "follow_recurrence": True})
        to_update |= self.env["calendar.recurrence"].create(recurrence_vals)
        return to_update._apply_recurrence()

    def _get_recurrence_params(self):
        """Recurrence parameters derived from this event's own start date."""
        if not self:
            return {}
        return self._get_recurrence_params_by_date(self._get_start_date())

    @api.model
    def _get_recurrence_params_by_date(self, event_date):
        """Return the recurrence parameters from a date object."""
        weekday_field_name = weekday_to_field(event_date.weekday())
        return {
            weekday_field_name: True,
            "weekday": weekday_field_name.upper(),
            "byday": str(get_weekday_occurence(event_date)),
            "day": event_date.day,
        }

    def _break_recurrence(self, future=True):
        """Breaks the event's recurrence.
        Stop the recurrence at the current event if `future` is True, leaving past events in the recurrence.
        If `future` is False, all events in the recurrence are detached and the recurrence itself is unlinked.
        :return: detached events excluding the current events
        """
        recurrences_to_unlink = self.env["calendar.recurrence"]
        detached_events = self.env["calendar.event"]
        for event in self:
            recurrence = event.recurrence_id
            if future:
                detached_events |= recurrence._stop_at(event)
            else:
                detached_events |= recurrence.calendar_event_ids
                recurrence.calendar_event_ids.recurrence_id = False
                recurrences_to_unlink |= recurrence
        recurrences_to_unlink.with_context(archive_on_error=True).unlink()
        return detached_events - self

    def _get_time_update_dict(self, base_event, time_values):
        """Return the update dictionary for shifting the base_event's time to the new date."""
        if not base_event:
            raise UserError(_("You can't update a recurrence without base event."))
        [base_time_values] = base_event.read(["start", "stop", "allday"])
        update_dict = {}
        start_update = fields.Datetime.to_datetime(time_values.get("start"))
        stop_update = fields.Datetime.to_datetime(time_values.get("stop"))
        allday = base_time_values["allday"]
        # Convert the base_event_id hours according to new values: time shift.
        # For an allday base event the hour component is meaningless, so shift
        # by whole days only (date - date) instead of a full datetime delta,
        # which would otherwise carry a spurious hour/minute offset into
        # start/stop.
        if start_update or stop_update:
            if start_update:
                if allday:
                    start = base_time_values["start"] + (
                        start_update.date() - self.start.date()
                    )
                    stop = base_time_values["stop"] + (
                        start_update.date() - self.start.date()
                    )
                else:
                    start = base_time_values["start"] + (start_update - self.start)
                    stop = base_time_values["stop"] + (start_update - self.start)
                start_date = base_time_values["start"].date() + (
                    start_update.date() - self.start.date()
                )
                stop_date = base_time_values["stop"].date() + (
                    start_update.date() - self.start.date()
                )
                update_dict.update(
                    {
                        "start": start,
                        "start_date": start_date,
                        "stop": stop,
                        "stop_date": stop_date,
                    }
                )
            if stop_update:
                if not start_update:
                    # Apply the same shift for start
                    if allday:
                        start = base_time_values["start"] + (
                            stop_update.date() - self.stop.date()
                        )
                    else:
                        start = base_time_values["start"] + (stop_update - self.stop)
                    start_date = base_time_values["start"].date() + (
                        stop_update.date() - self.stop.date()
                    )
                    update_dict.update({"start": start, "start_date": start_date})
                if allday:
                    stop = base_time_values["stop"] + (
                        stop_update.date() - self.stop.date()
                    )
                else:
                    stop = base_time_values["stop"] + (stop_update - self.stop)
                stop_date = base_time_values["stop"].date() + (
                    stop_update.date() - self.stop.date()
                )
                update_dict.update({"stop": stop, "stop_date": stop_date})
        return update_dict

    @api.model
    def _prepare_archive_values(self):
        """Return parameters for archiving events in calendar module."""
        return {"active": False}

    @api.model
    def _has_values_to_sync(self, values):
        """Method to be overriden: return candidate values to be synced within rewrite_recurrence function scope."""
        return False

    @api.model
    def _prepare_update_future_events_values(self):
        """Return parameters for updating future events within _update_future_events function scope."""
        return {}

    @api.model
    def _prepare_remove_sync_id_values(self):
        """Return parameters for removing event synchronization id within _update_future_events function scope."""
        return {}

    def _get_updated_recurrence_values(self, new_start_date):
        """Copy values from current recurrence and update the start date weekday."""
        [previous_recurrence_values] = self.recurrence_id.copy_data()
        if self.start.weekday() != new_start_date.weekday():
            previous_recurrence_values.pop(weekday_to_field(self.start.weekday()), None)
        return previous_recurrence_values

    def _update_future_events(self, values, time_values, recurrence_values):
        """
        Trim the current recurrence detaching the occurrences after current event,
        deactivate the detached events except for the updated event and apply recurrence values.

        :return: the event the resulting series is rooted at.
        """
        self.check_singleton()
        base_event = self
        update_dict = self._get_time_update_dict(base_event, time_values)
        time_values.update(update_dict)
        # Get base values from the previous recurrence and update the start date weekday field.
        start_date = (
            time_values["start"].date() if "start" in time_values else self.start.date()
        )
        previous_recurrence_values = self._get_updated_recurrence_values(start_date)

        # Trim previous recurrence at current event, deleting following events except for the updated event.
        detached_events_split = self.recurrence_id._stop_at(self)
        (detached_events_split - self).write(
            {"active": False, **self._prepare_remove_sync_id_values()}
        )

        # Update the current event with the new recurrence information.
        if values or time_values:
            # `skip_attendee_notification`, as `_rewrite_recurrence` already
            # does on its own inner write: this is a nested `write` carrying the
            # new `start`, so it announces the move a second time on top of the
            # one the outer `write` sends. The outer one is the one to keep --
            # it is the only one rendered with the recurrence described, the
            # whole point of `calendar_template_ignore_recurrence`.
            self.with_context(skip_attendee_notification=True).write(
                {
                    **time_values,
                    **values,
                    **self._prepare_remove_sync_id_values(),
                    **self._prepare_update_future_events_values(),
                }
            )
            if time_values:
                # Reset attendees state to pending and accept event for current user.
                self._reset_attendees_status()

        # Combine parameters from previous recurrence with the new recurrence parameters.
        new_values = {
            **previous_recurrence_values,
            **self._get_recurrence_params_by_date(start_date),
            **recurrence_values,
            "repeat_number": recurrence_values.get("repeat_number", 0)
            or len(detached_events_split),
        }
        new_values.pop("rrule", None)

        # Generate the new recurrence by patching the updated event.
        self._apply_recurrence_values(new_values)
        # `self` is the base event of the series this just built; `write` mails
        # the attendees from it.
        return self

    def _rewrite_recurrence(self, values, time_values, recurrence_values):
        """Delete the current recurrence, reactivate base event and apply updated recurrence values.

        :return: the event the resulting series is rooted at. It is the *base*
            event, which is not necessarily ``self``: every occurrence is
            archived and the series rebuilt from the base, so a write on any
            other occurrence leaves ``self`` archived and detached.
        """
        self.check_singleton()
        base_event = (
            self.recurrence_id.base_event_id
            or self.recurrence_id._get_first_event(include_outliers=False)
        )
        update_dict = self._get_time_update_dict(base_event, time_values)
        time_values.update(update_dict)

        if self._has_values_to_sync(values) or time_values or recurrence_values:
            # Get base values from the previous recurrence and update the start date weekday field.
            start_date = (
                time_values["start"].date()
                if "start" in time_values
                else self.start.date()
            )
            old_recurrence_values = self._get_updated_recurrence_values(start_date)

            # Archive all events and delete recurrence, reactivate base event and apply updated values.
            base_event.action_mass_archive("all")
            base_event.recurrence_id.unlink()
            base_event.with_context(skip_attendee_notification=True).write(
                {"active": True, "recurrence_id": False, **values, **time_values}
            )

            if time_values:
                # Reset attendees state to pending and accept event for current user.
                base_event._reset_attendees_status()

            # Combine parameters from previous recurrence with the new recurrence parameters.
            new_values = {
                **old_recurrence_values,
                **base_event._get_recurrence_params(),
                **recurrence_values,
            }
            new_values.pop("rrule", None)

            # Patch base event with updated recurrence parameters: this will recreate the recurrence.
            detached_events = base_event._apply_recurrence_values(new_values)
            detached_events.write({"active": False})
        else:
            # Write on all events. Carefull, it could trigger a lot of noise to Google/Microsoft...
            self.recurrence_id._write_events(values)
        return base_event

    # ------------------------------------------------------------
    # MANAGEMENT
    # ------------------------------------------------------------

    def change_attendee_status(self, status, recurrence_update_setting):
        self.check_singleton()
        if recurrence_update_setting == "all":
            events = self.recurrence_id.calendar_event_ids
        elif recurrence_update_setting == "subsequent":
            events = self.recurrence_id.calendar_event_ids.filtered(
                lambda ev: ev.start >= self.start
            )
        else:
            events = self
        attendee = events.attendee_ids.filtered(
            lambda x: x.partner_id == self.env.user.partner_id
        )
        if status == "accepted":
            return attendee.do_accept()
        if status == "declined":
            return attendee.do_decline()
        return attendee.do_tentative()

    def find_partner_customer(self):
        """Return the first attendee partner that is not the organizer.

        :rtype: res.partner
        :return: the contact partner, or an empty res.partner recordset (the
            sentinel matches the return type, so callers can read e.g. `.name`
            on the result even when there is no such partner).
        """
        self.check_singleton()
        return next(
            (
                attendee.partner_id
                for attendee in self.attendee_ids
                if attendee.partner_id != self.user_id.partner_id
            ),
            self.env["res.partner"],
        )

    # ------------------------------------------------------------
    # TOOLS
    # ------------------------------------------------------------

    @api.model
    def _get_activity_excluded_models(self):
        """
        For some models, we don't want to automatically create activities when a calendar.event is created.
        (This is the case notably for appointment.types)
        This hook method allows to specify those models.
        See calendar.event create method for details.
        """
        return []

    def _reset_attendees_status(self):
        """Reset attendees status to pending and accept event for current user."""
        for attendee in self.attendee_ids:
            if attendee.partner_id == self.env.user.partner_id:
                attendee.state = "accepted"
            else:
                attendee.state = "needsAction"

    def _get_start_date(self):
        """Return the event starting date in the event's timezone.
        If no starting time is assigned (yet), return today as default
        :return: date
        """
        if not self.start:
            return fields.Date.today()
        if self.recurrency and self.event_tz:
            tz = timezone(self.event_tz)
            # Ensure that all day events date are not calculated around midnight. TZ shift would potentially return bad date
            start = self.start if not self.allday else self.start.replace(hour=12)
            return start.replace(tzinfo=UTC).astimezone(tz).date()
        return self.start.date()

    def _range(self):
        self.check_singleton()
        return (self.start, self.stop)

    def get_display_time_tz(self, tz=False):
        """get the display_time of the meeting, forcing the timezone. This method is called from email template, to not use sudo()."""
        self.check_singleton()
        if tz:
            self = self.with_context(tz=tz)
        return self._get_display_time(self.start, self.stop, self.duration, self.allday)

    def _get_ics_file(self):
        """Returns iCalendar file for the event invitation.
        :returns a dict of .ics file content for each meeting
        """
        result = {}

        def ics_datetime(idate):
            return idate.replace(tzinfo=timezone("UTC")) if idate else False

        if not vobject:
            return result

        for meeting in self:
            cal = vobject.iCalendar()
            event = cal.add("vevent")

            if not meeting.start or not meeting.stop:
                raise UserError(
                    _("First you have to specify the date of the invitation.")
                )
            event.add("created").value = ics_datetime(fields.Datetime.now())
            if meeting.allday:
                # An all-day event is a DATE, not a time of day. `start`/`stop`
                # hold 08:00 and 18:00 by this module's own convention (see
                # `_inverse_dates`), and handing those naive datetimes to
                # vobject emitted `DTSTART:20301224T080000` -- a *floating*
                # datetime, which a reader shifts into its own timezone. So
                # Christmas arrived as "08:00 to 18:00, in whatever zone the
                # reader happens to be", the exact reading the convention
                # exists to avoid.
                #
                # DTEND is exclusive for a DATE value (RFC 5545 3.8.2.2), so a
                # 24th-to-26th event ends on the 27th. Emitting the 26th made
                # every multi-day all-day event a day short.
                _add_ics_date(event, "dtstart", meeting.start.date())
                _add_ics_date(event, "dtend", meeting.stop.date() + timedelta(days=1))
            else:
                event.add("dtstart").value = ics_datetime(meeting.start)
                event.add("dtend").value = ics_datetime(meeting.stop)
            event.add("summary").value = meeting._get_customer_summary()
            description = html2plaintext(meeting._get_customer_description())
            if description:
                event.add("description").value = description
            if meeting.location:
                event.add("location").value = meeting.location
            if meeting._ics_should_declare_recurrence() and (
                rrule_value := self._get_ics_rrule(meeting.rrule)
            ):
                event.add("rrule").value = rrule_value

            meeting._ics_add_alarms(event)
            meeting._ics_add_people(event)

            result[meeting.id] = cal.serialize().encode("utf-8")

        return result

    def _ics_add_alarms(self, vevent):
        """Add one VALARM per reminder, triggered relative to the start."""
        self.check_singleton()
        for alarm in self.alarm_ids:
            valarm = vevent.add("valarm")
            trigger = valarm.add("TRIGGER")
            trigger.params["related"] = ["START"]
            trigger.value = -timedelta(minutes=alarm.duration_minutes)
            valarm.add("DESCRIPTION").value = alarm.name or "Odoo"

    def _ics_add_people(self, vevent):
        """Add the ATTENDEE lines and, where there is an address, ORGANIZER."""
        self.check_singleton()
        for attendee in self.attendee_ids:
            vevent.add("attendee").value = "MAILTO:" + (attendee.email or "")
        if self.partner_id.email:
            organizer = vevent.add("organizer")
            organizer.value = "MAILTO:" + self.partner_id.email
            if self.partner_id.name:
                organizer.params["CN"] = [
                    self.partner_id.display_name.replace('"', "'")
                ]

    def _ics_should_declare_recurrence(self):
        """Whether this event's .ics may carry the series' RRULE.

        Odoo materialises every occurrence as its own `calendar.event` row, so
        an RRULE in an occurrence's .ics does not describe it -- it asks the
        reading client to *generate* the siblings that already exist. Emitting
        one per occurrence multiplies the series by itself: three daily
        occurrences each declaring ``FREQ=DAILY;COUNT=3`` is nine events.

        This went unnoticed because the RRULE was malformed (see
        `_get_ics_rrule`) and clients dropped it. Making it well-formed is what
        makes the over-declaration bite, so the two belong together.

        Two conditions, and both are needed:

        - only the recurrence's **base event** stands for the series; every
          other occurrence is one event and exports as one.
        - not when `calendar_template_ignore_recurrence` is set, which is the
          module's existing way of saying "this mail is about this occurrence,
          not about the series" -- `_send_reminder` sets it for every reminder,
          and `_write_notify_attendees` for a single-occurrence move.
        """
        self.check_singleton()
        if not self.rrule or self.env.context.get(
            "calendar_template_ignore_recurrence"
        ):
            return False
        # A recurrent event with no recurrence record yet is its own base.
        return not self.recurrence_id or self == self.recurrence_id.base_event_id

    @api.model
    def _get_ics_rrule(self, rrule):
        """The RRULE value fit for a single iCalendar RRULE property.

        The payload comes from `calendar.recurrence._rrule_value`, which owns
        the two shapes the stored column can hold -- see its docstring for why
        one of them prefixes a meaningless DTSTART. Assigning the whole block to
        an `RRULE` property emitted **two** RRULE lines, the first of them
        ``RRULE:DTSTART:<the compute's timestamp>``, so a client reading the
        invitation took a bare DTSTART as the recurrence rule and the meeting
        arrived with its repetition broken.

        `UNTIL` is stamped UTC here and not in the stored value: RFC 5545
        requires it when DTSTART is a UTC datetime, which is how `_get_ics_file`
        writes it, but the stored rule is not an iCalendar document and
        `_rrule_parse` reads it back against a naive `dtstart`.

        :rtype: str
        """
        value = self.env["calendar.recurrence"]._rrule_value(rrule)
        return re.sub(r"(UNTIL=\d{8}T\d{6})($|;)", r"\1Z\2", value)

    @api.model
    def _get_contact_details_description(self, organizer, partners):
        """Build sanitized HTML with the organizer details and the details
        of the contact partner (the first partner which is not the organizer).
        """
        odoobot = self.env.ref("base.user_root")
        contact_description = []
        # Organizer
        if organizer and organizer != odoobot:
            contact_description.extend(
                self._prepare_partner_contact_details_html(
                    _("Organized by"), organizer.partner_id
                )
            )
        # First contact partner
        first_partner = partners.filtered(
            lambda partner: partner not in (odoobot.partner_id + organizer.partner_id)
        )[:1]
        if first_partner:
            if contact_description:
                contact_description.append(
                    ""
                )  # To add a blank line between the organizer and partner details
            contact_description.extend(
                self._prepare_partner_contact_details_html(
                    _("Contact Details"), first_partner
                )
            )
        return Markup("<br/>").join(contact_description)

    @api.model
    def _prepare_partner_contact_details_html(self, section_title, partner):
        details = list(
            filter(
                None,
                [
                    partner.name,
                    partner.email
                    and Markup("<a href='mailto:%(email)s'>%(email)s</a>")
                    % {"email": partner.email},
                    partner._phone_get_number().number
                    and Markup("<a href='tel:%(phone)s'>%(phone)s</a>")
                    % {"phone": partner._phone_get_number().number},
                ],
            )
        )
        if details:
            details.insert(0, Markup("<strong>%s</strong>") % section_title)
        return details

    def _get_customer_description(self):
        """
        :rtype: str
        :returns: html Sanitized HTML description for customer to include in calendar exports
        """
        return (
            html_sanitize(self.description)
            if not is_html_empty(self.description)
            else ""
        )

    def _get_customer_summary(self):
        """
        :rtype: str
        :returns: The summary to include in calendar exports
        """
        return self.name or ""

    @api.model
    def _get_display_time(self, start, stop, zduration, zallday):
        """Return date and time (from to from) based on duration with timezone in string. Eg :
        1) if user add duration for 2 hours, return : August-23-2013 at (04-30 To 06-30) (Europe/Brussels)
        2) if event all day ,return : AllDay, July-31-2013
        """
        tz_name = self.env.context.get("tz") or self.env.user.partner_id.tz or "UTC"

        # get date/time format according to context
        format_date, format_time = self._get_date_formats()

        # convert date and time into user timezone
        self_tz = self.with_context(tz=tz_name)
        date = fields.Datetime.context_timestamp(
            self_tz, fields.Datetime.from_string(start)
        )
        date_deadline = fields.Datetime.context_timestamp(
            self_tz, fields.Datetime.from_string(stop)
        )

        # convert into string the date and time, using user formats
        date_str = date.strftime(format_date)
        time_str = date.strftime(format_time)

        if zallday:
            display_time = _("All Day, %(day)s", day=date_str)
        elif zduration < 24:
            duration = date + timedelta(minutes=round(zduration * 60))
            duration_time = duration.strftime(format_time)
            display_time = _(
                "%(day)s at (%(start)s To %(end)s) (%(timezone)s)",
                day=date_str,
                start=time_str,
                end=duration_time,
                timezone=tz_name,
            )
        else:
            dd_date = date_deadline.strftime(format_date)
            dd_time = date_deadline.strftime(format_time)
            display_time = _(
                "%(date_start)s at %(time_start)s To\n %(date_end)s at %(time_end)s (%(timezone)s)",
                date_start=date_str,
                time_start=time_str,
                date_end=dd_date,
                time_end=dd_time,
                timezone=tz_name,
            )
        return display_time

    def _get_duration(self, start, stop):
        """Get the duration value between the 2 given dates."""
        if not start or not stop:
            return 0
        duration = (stop - start).total_seconds() / 3600
        return round(duration, 2)

    @api.model
    def _get_date_formats(self):
        """get current date and time format, according to the context lang
        :return: a tuple with (format date, format time)
        """
        lang = get_lang(self.env)
        return (lang.date_format, lang.time_format)

    @api.model
    def _get_fields_recurrent(self):
        return {
            "byday",
            "repeat_until",
            "repeat_unit",
            "month_by",
            "event_tz",
            "rrule",
            "repeat_interval",
            "repeat_number",
            "repeat_type",
            "mon",
            "tue",
            "wed",
            "thu",
            "fri",
            "sat",
            "sun",
            "day",
            "weekday",
        }

    @api.model
    def _get_fields_time(self):
        return {"start", "stop", "start_date", "stop_date"}

    @api.model
    def _touches_time(self, values):
        """Whether `values` moves the event in time.

        `write` used to ask this twice, eleven lines apart, in two spellings
        that disagree for a falsy value: `any(values.get(f) for f in ...)`
        (truthiness) decided whether to reschedule alarms, while
        `any({f: values.get(f) for f in ... if f in values})` -- which iterates
        the dict's *keys*, so it is a presence test whose values are decoration
        -- decided whether to detach the event from its recurrence. Writing
        `{'start_date': False}` therefore detached an event that had not moved.
        One predicate, truthiness, used by both.
        """
        return any(values.get(fname) for fname in self._get_fields_time())

    @api.model
    def _get_fields_custom(self):
        all_fields = self.fields_get(attributes=["manual"])
        return {fname for fname in all_fields if all_fields[fname]["manual"]}

    @api.model
    def _get_fields_public(self):
        return (
            self._get_fields_recurrent()
            | self._get_fields_time()
            | self._get_fields_custom()
            | {
                "id",
                "active",
                "allday",
                "duration",
                "user_id",
                "repeat_interval",
                "partner_id",
                "repeat_number",
                "rrule",
                "recurrence_id",
                "show_as",
                "privacy",
            }
        )

    @api.model
    def get_default_duration(self):
        """The configured default meeting length, in hours.

        Read through `ir.default._get_model_defaults`, which is `ormcache`d --
        one query cold, none warm. This used to spell the precedence out by
        hand as four `ir.default._get` calls -- (user, company), (user),
        (company), global -- and each of those is an uncached `search`, so it
        cost **four queries on every call**, warm, from every `default_get`
        (`_default_stop` asks for it).

        `_get_model_defaults` answers the same question: its
        ``ORDER BY (user_id IS NOT NULL) DESC, (company_id IS NOT NULL) DESC,
        id`` with first-row-wins per field is that same precedence, and it
        returns the whole model's defaults rather than one field's.
        """
        defaults = self.env["ir.default"].sudo()._get_model_defaults("calendar.event")
        return defaults.get("duration") or 1

    def _update_access_token(self):
        """Rotate the credential used only to join this event's conference."""
        for event in self:
            event.access_token = generate_calendar_token()

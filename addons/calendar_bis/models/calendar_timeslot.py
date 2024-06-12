import logging

from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
from pytz import timezone

from odoo import models, fields, api, _, Command
from odoo.exceptions import AccessError, UserError
from odoo.tools import pycompat
from odoo.addons.base.models.res_partner import _tz_get

_logger = logging.getLogger(__name__)

try:
    import vobject
except ImportError:
    _logger.warning("`vobject` Python module not found, iCal file generation disabled. Consider installing this module if you want to generate iCal files")
    vobject = None

days = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']

class CalendarTimeslot(models.Model):
    _name = "calendar.timeslot"
    _description = "Calendar Timeslot"
    _order = "start asc, id"

    # Technical Fields
    event_id = fields.Many2one('calendar.event_bis')    # NOT REQUIRED See make_timeslots
    can_read_private = fields.Boolean(compute='_compute_access', default=True)
    can_write = fields.Boolean(compute='_compute_access', default=True)
    active = fields.Boolean(default=True)
    edit = fields.Selection([('one', 'This event only'),            # This field is used to determine the edit policy
                             ('post', 'All event after this one'),  # when editing a recurring event
                             ('all', 'All events in the series')], default='all', store=False)

    # Time Related Fields
    start = fields.Datetime(default=fields.Datetime.now, required=True)
    stop = fields.Datetime(default=fields.Datetime.now() + relativedelta(minutes=15), required=True, compute='_compute_stop', readonly=False, store=True)
    duration = fields.Float('Duration', compute='_compute_duration', store=True, readonly=False)
    allday = fields.Boolean('All Day', default=False)
    tz = fields.Selection(_tz_get, string='Timezone', related='partner_id.tz')

    # Attendee Fields
    attendee_ids = fields.One2many('calendar.attendee_bis', 'timeslot_id', compute='_compute_attendee_ids', store=True, copy=True)
    partner_ids = fields.Many2many('res.partner', string="Attendees")   # TODO move to calendar_ev

    # Computed Fields
    is_current_partner = fields.Boolean(compute='_compute_is_current_partner')
    is_organizer_alone = fields.Boolean(compute='_compute_is_organizer_alone')

    # Event Related Fields
        # Public fields
    is_public = fields.Boolean(related='event_id.is_public', readonly=False)
    is_shown = fields.Boolean(related='event_id.is_shown', default=True, readonly=False)
    partner_id = fields.Many2one('res.partner', related='event_id.partner_id', string='Calendar', readonly=False, default=lambda self: self.env.user.partner_id.id)
    user_id = fields.Many2one('res.users', related='event_id.user_id', string='User')
        # Private fields
    name = fields.Char('Title', compute='_compute_name', inverse='_inverse_name', required=True)
    description = fields.Char('Note', compute='_compute_description', inverse='_inverse_description')
    tag_ids = fields.Many2many('calendar.event_bis.tag', compute='_compute_tag_ids', inverse='_inverse_tag_ids', string="Tags")
    location = fields.Char('Location', compute='_compute_location', inverse='_inverse_location', tracking=True)
    alarm_ids = fields.Many2many('calendar.alarm_ids', compute='_compute_alarm_ids', inverse='_inverse_alarm_ids', string="Alerts")

    # Recurrence Related Fields
    # /!\ These fields must be computed and inverse in the same method,
    # DO NOT separate them, DO NOT add fields to their compute or inverse method
    is_recurring = fields.Boolean('Recurrent', compute="_compute_recurring", inverse="_inverse_recurring")
    mon = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    tue = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    wed = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    thu = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    fri = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    sat = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    sun = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    freq = fields.Selection([('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly')],
                            string='Frequency', default='weekly', compute="_compute_recurring", inverse="_inverse_recurring")
    until = fields.Datetime('End Date', compute="_compute_recurring", inverse="_inverse_recurring") # TODO Move to Date instead of datetime ?
    count = fields.Integer(compute="_compute_recurring", inverse="_inverse_recurring")
    interval = fields.Integer(compute="_compute_recurring", inverse="_inverse_recurring")
    monthday = fields.Integer('Nth of the month', compute="_compute_recurring", inverse="_inverse_recurring")               # 3rd of the month
    monthweekday_n = fields.Integer('Weekday of the month', compute="_compute_recurring", inverse="_inverse_recurring")     # "1ST" Monday of the month
    monthweekday_day = fields.Selection([('mon', 'Monday'), ('tue', 'Tuesday'), ('wed', 'Wednesday'),                       # 1st "MONDAY" of the month
        ('thu', 'Thursday'), ('fri', 'Friday'), ('sat', 'Saturday'), ('sun', 'Sunday')], string='Weekday of the month',
                                        compute="_compute_recurring", inverse="_inverse_recurring")

    def write(self, values):
        # If event_id is in values:
        # - we are in make_timeslots or break_after and don't need to recompute start/stop values
        if 'event_id' in values:
            return super().write(values)

        # If event_id is not in values, we are editing a timeslot
        edit = values.pop('edit', 'all')
        batch = self.env['calendar.timeslot']
        if 'start' in values and isinstance(values['start'], str):
            values['start'] = datetime.fromisoformat(values['start'])
        if 'stop' in values and isinstance(values['stop'], str):
            values['stop'] = datetime.fromisoformat(values['stop'])

        # We try to batch as much as possible, but we need to handle change in date for recurring events
        # If you modify one event: remove it from the recurrence and write on it
        # If you modify part events: remove part events from the recurrence, if start/stop is modified also apply each change individually
        # If you modify all events: if start/stop is modified also apply each change individually
        for slot in self:
            if not slot.is_recurring:
                batch += slot
            elif edit == 'one':
                slot.event_id.exdate(slot)
                batch += slot
            elif edit in ['post', 'all']:
                if edit == 'post':
                    slot.event_id.break_after(slot)
                if 'start' not in values and 'stop' not in values:
                    batch += slot.event_id.timeslot_ids
                else:
                    start = values.get('start', slot.start)
                    start_delta = start - slot.start
                    stop = values.get('stop', slot.stop)
                    duration = max(values.get('duration', (stop - start).total_seconds() / 3600), 1/60)
                    new_vals = {**values.copy(), 'duration': duration}
                    for slot in slot.event_id.timeslot_ids:
                        if start_delta:
                            new_vals['start'] = slot.start + start_delta
                        super(CalendarTimeslot, slot).write(new_vals)
                        # TODO set attendee status to ???
                    slot.update_recurrence_start(start, start_delta)
        return super(CalendarTimeslot, batch).write(values)

    @api.model_create_multi
    def create(self, values):
        for vals in values:
            vals['event_id'] = vals.get('event_id') or self.env['calendar.event_bis'].create([{}]).id
        return super().create(values)

    # ACCESS FUNCTIONS
    def _filter_has_access(self, access):
        res = check_acl = self.env['calendar.timeslot']
        for slot in self:
            if isinstance(slot.id, models.NewId):
                res += slot
                continue
            if not slot.event_id:
                continue
            check_acl += slot
        return res + check_acl.event_id._filter_access_rules(access).timeslot_ids

    @api.depends_context('uid')
    @api.depends('event_id')
    def _compute_access(self):
        self.can_read_private = False
        self.can_write = False
        self._filter_has_access('read').can_read_private = True
        self._filter_has_access('write').can_write = True

    # DRAG AND DROP
    def update_recurrence_start(self, dt, delta=None):  # TODO rename
        if not self.is_recurring:
            return
        elif self.freq in ['daily', 'yearly']:
            self.event_id.make_timeslots()
        elif self.freq == 'weekly':
            self.event_id.write({
                days[(dt - delta).weekday()]: False,
                days[dt.weekday()]: True,
            })
            # write will trigger make_timeslots
        elif self.freq == 'monthly':
            self.monthday = dt.day
            # TODO monthweekday
            self.event_id.make_timeslots()

    # RECURRING RELATED
    # /!\ These fields must be computed and inverse in the same method,
    # DO NOT separate them, DO NOT add fields to their compute or inverse method
    @api.depends('event_id')
    def _compute_recurring(self):
        for timeslot in self:
            timeslot.update({
                'is_recurring': timeslot.event_id.is_recurring,
                'mon': timeslot.event_id.mon,
                'tue': timeslot.event_id.tue,
                'wed': timeslot.event_id.wed,
                'thu': timeslot.event_id.thu,
                'fri': timeslot.event_id.fri,
                'sat': timeslot.event_id.sat,
                'sun': timeslot.event_id.sun,
                'freq': timeslot.event_id.freq,
                'until': timeslot.event_id.until,
                'count': timeslot.event_id.count,
                'interval': timeslot.event_id.interval,
                'monthday': timeslot.event_id.monthday,
                'monthweekday_n': timeslot.event_id.monthweekday_n,
                'monthweekday_day': timeslot.event_id.monthweekday_day,
            })

    def _inverse_recurring(self):
        for timeslot in self:
            timeslot.event_id.write({
                'is_recurring': timeslot.is_recurring,
                'mon': timeslot.mon,
                'tue': timeslot.tue,
                'wed': timeslot.wed,
                'thu': timeslot.thu,
                'fri': timeslot.fri,
                'sat': timeslot.sat,
                'sun': timeslot.sun,
                'freq': timeslot.freq,
                'until': timeslot.until,
                'count': timeslot.count,
                'interval': timeslot.interval,
                'monthday': timeslot.monthday,
                'monthweekday_n': timeslot.monthweekday_n,
                'monthweekday_day': timeslot.monthweekday_day,
            })

    # COMPUTES
    @api.depends('duration')
    def _compute_stop(self):
        for slot in self:
            slot.stop = slot.start + relativedelta(hours=slot.duration)

    @api.depends('stop', 'start')
    def _compute_duration(self):
        for slot in self:
            slot.duration = (slot.stop - slot.start).total_seconds() / 3600

    #### RELATED ####
    @api.depends('event_id.name')
    @api.depends_context('uid')
    def _compute_name(self):
        has_access = self.filtered('can_read_private')
        (self - has_access).name = _('Busy')
        for slot in has_access:
            slot.name = slot.event_id.name

    def _inverse_name(self):
        for slot in self:
            slot.event_id.name = slot.name

    @api.depends('event_id.description')
    @api.depends_context('uid')
    def _compute_description(self):
        for slot in self.filtered('can_read_private'):
            slot.description = slot.event_id.description

    def _inverse_description(self):
        for slot in self:
            slot.event_id.description = slot.description

    @api.depends('partner_ids')
    def _compute_attendee_ids(self):
        for slot in self:
            need_to_add = slot.partner_id + slot.partner_ids._origin - slot.attendee_ids.partner_id
            if need_to_add:
                slot.attendee_ids = [Command.create(
                    {'partner_id': partner.id, 'state': 'yes' if partner.id == slot.partner_id.id else 'maybe'}
                ) for partner in need_to_add]

    @api.depends('event_id.tag_ids')
    @api.depends_context('uid')
    def _compute_tag_ids(self):
        for slot in self.filtered('can_read_private'):
            slot.tag_ids = slot.event_id.tag_ids

    def _inverse_tag_ids(self):
        for slot in self:
            slot.event_id.tag_ids = slot.tag_ids

    @api.depends('event_id.alarm_ids')
    @api.depends_context('uid')
    def _compute_alarm_ids(self):
        for slot in self.filtered('can_read_private'):
            slot.alarm_ids = slot.event_id.alarm_ids

    def _inverse_alarm_ids(self):
        for slot in self:
            slot.event_id.alarm_ids = slot.alarm_ids

    @api.depends('event_id.location')
    @api.depends_context('uid')
    def _compute_location(self):
        for slot in self.filtered('can_read_private'):
            slot.location = slot.event_id.location

    def _inverse_location(self):
        for slot in self:
            slot.event_id.location = slot.location

    def _compute_is_current_partner(self):
        self.is_current_partner = False
        partner_id = self.env.context.get('active_model') == 'res.partner' and self.env.context.get('active_id')
        if partner_id:
            self.filtered(lambda ts: partner_id in ts.partner_ids.mapped('ids')).is_current_partner = True

    @api.depends('partner_id', 'attendee_ids')
    def _compute_is_organizer_alone(self):
        """ Check if there are other attendees who all have declined the event"""
        for ts in self:
            other_attendees_reply = ts.attendee_ids.filtered(lambda a: a.partner_id != ts.partner_id).mapped('state')
            if other_attendees_reply and all([reply == 'no' for reply in other_attendees_reply]):
                ts.is_organizer_alone = True
            else:
                ts.is_organizer_alone = False

    def _get_attendee_emails(self):
        """ Get comma-separated attendee email addresses. """
        self.ensure_one()
        return ",".join(e for e in self.attendee_ids.mapped("email") if e)

    def _get_display_time(self, tz=None):
        """ Return date and time (from to from) based on duration with timezone in string. Eg :
                1) if user add duration for 2 hours, return : August-23-2013 at (04-30 To 06-30) (Europe/Brussels)
                2) if event all day ,return : AllDay, July-31-2013
        """
        self.ensure_one()
        timezone = tz or self.env.user.partner_id.tz or 'UTC'

        # get date/time format according to context
        format_date, format_time = self._get_date_formats()

        # convert date and time into user timezone
        self_tz = self.with_context(tz=timezone)
        date = fields.Datetime.context_timestamp(self_tz, fields.Datetime.from_string(self.start))
        date_deadline = fields.Datetime.context_timestamp(self_tz, fields.Datetime.from_string(self.stop))

        # convert into string the date and time, using user formats
        to_text = pycompat.to_text
        date_str = to_text(date.strftime(format_date))
        time_str = to_text(date.strftime(format_time))

        if self.allday:
            display_time = _("All Day, %(day)s", day=date_str)
        elif self.duration < 24:
            duration = date + timedelta(minutes=round(self.duration*60))
            duration_time = to_text(duration.strftime(format_time))
            display_time = _(
                u"%(day)s at (%(start)s To %(end)s) (%(timezone)s)",
                day=date_str,
                start=time_str,
                end=duration_time,
                timezone=timezone,
            )
        else:
            dd_date = to_text(date_deadline.strftime(format_date))
            dd_time = to_text(date_deadline.strftime(format_time))
            display_time = _(
                u"%(date_start)s at %(time_start)s To\n %(date_end)s at %(time_end)s (%(timezone)s)",
                date_start=date_str,
                time_start=time_str,
                date_end=dd_date,
                time_end=dd_time,
                timezone=timezone,
            )
        return display_time

    def _get_ics(self):
        def ics_datetime(date, allday=False):
            if not date:
                return
            if allday:
                return date
            return date.replace(tzinfo=timezone('UTC'))

        result = {}

        if not vobject:
            return result

        for ts in self:
            cal = vobject.iCalendar()
            event = cal.add('vevent')

            if not ts.start or not ts.stop:
                raise UserError(_("First you have to specify the date of the invitation."))
            event.add('created').value = ics_datetime(fields.Datetime.now())
            event.add('dtstart').value = ics_datetime(ts.start, ts.allday)
            event.add('dtend').value = ics_datetime(ts.stop, ts.allday)
            event.add('summary').value = ts.name        # TODO overridable
            description = ts.description if ts.description else ''    # TODO overridable + html2plaintext
            if description:
                event.add('description').value = description
            if ts.location:
                event.add('location').value = ts.location
            if ts.is_recurring:
                event.add('rrule').value = ts.event_id.rrule

            if ts.alarm_ids:
                for alarm in ts.alarm_ids:
                    valarm = event.add('valarm')
                    trigger = valarm.add('TRIGGER')
                    trigger.params['related'] = ["START"]
                    trigger.value = alarm.time_delta
                    valarm.add('DESCRIPTION').value = alarm.name or u'Odoo'
            for attendee in ts.attendee_ids:
                att = event.add('attendee')
                att.value = u'MAILTO:' + (attendee.email or u'')

            # Add "organizer" field if email available
            if ts.partner_id.email:
                organizer = event.add('organizer')
                organizer.value = u'MAILTO:' + ts.partner_id.email
                if ts.partner_id.name:
                    organizer.params['CN'] = [ts.partner_id.display_name.replace('\"', '\'')]
            result[ts.id] = cal.serialize().encode('utf-8')
        return result

    def mass_delete(self, update_policy):
        self.ensure_one()
        if not self.can_write:
            raise AccessError(_("You don't have access to delete this timeslot."))
        if update_policy == "all":
            return self.event_id.unlink()
        self.event_id.break_after(self).unlink()

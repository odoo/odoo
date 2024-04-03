from odoo import models, fields, api, _, Command
from odoo.exceptions import AccessError

from dateutil.relativedelta import relativedelta
from datetime import datetime

days = ['mo', 'tu', 'we', 'th', 'fr', 'sa', 'su']

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
                             ('all', 'All events in the series'),   # when editing a recurring event
                             ('post', 'All event after this one')], default='all', store=False)

    # Time Related Fields
    start = fields.Datetime(default=fields.Datetime.now, required=True)
    stop = fields.Datetime(default=fields.Datetime.now() + relativedelta(minutes=15), required=True, compute='_compute_stop', readonly=False, store=True)
    duration = fields.Float('Duration', compute='_compute_duration', store=True, readonly=False)
    allday = fields.Boolean('All Day', default=False)

    # Attendee Fields
    attendee_ids = fields.One2many('calendar.attendee_bis', 'timeslot_id', compute='_compute_attendee_ids', store=True, copy=True)
    partner_ids = fields.Many2many('res.partner', string="Attendees")

    # Event Related Fields
        # Public fields
    is_public = fields.Boolean(related='event_id.is_public', readonly=False)
    partner_id = fields.Many2one('res.partner', related='event_id.partner_id', string='Calendar', readonly=False, default=lambda self: self.env.user.partner_id.id)
    user_id = fields.Many2one('res.users', related='event_id.user_id', string='User')
        # Private fields
    name = fields.Char(compute='_compute_name', inverse='_inverse_name', required=True)
    note = fields.Char(compute='_compute_note', inverse='_inverse_note')
    tag_ids = fields.Many2many('calendar.event_bis.tag', compute='_compute_tag_ids', inverse='_inverse_tag_ids', string="Tags")

    # Recurrence Related Fields
    # /!\ These fields must be computed and inverse in the same method,
    # DO NOT separate them, DO NOT add fields to their compute or inverse method
    is_recurring = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    mo = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    tu = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    we = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    th = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    fr = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    sa = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    su = fields.Boolean(compute="_compute_recurring", inverse="_inverse_recurring")
    freq = fields.Selection([('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'), ('yearly', 'Yearly')],
                            string='Frequency', default='weekly', compute="_compute_recurring", inverse="_inverse_recurring")
    until = fields.Datetime(compute="_compute_recurring", inverse="_inverse_recurring") # TODO Move to Date instead of datetime ?
    count = fields.Integer(compute="_compute_recurring", inverse="_inverse_recurring")
    interval = fields.Integer(compute="_compute_recurring", inverse="_inverse_recurring")
    monthday = fields.Integer(compute="_compute_recurring", inverse="_inverse_recurring")               # 3rd of the month
    monthweekday_n = fields.Integer(compute="_compute_recurring", inverse="_inverse_recurring")         # "1ST" Monday of the month
    monthweekday_day = fields.Selection([('mo', 'Monday'), ('tu', 'Tuesday'), ('we', 'Wednesday'),      # 1st "MONDAY" of the month
        ('th', 'Thursday'), ('fr', 'Friday'), ('sa', 'Saturday'), ('su', 'Sunday')], compute="_compute_recurring", inverse="_inverse_recurring")

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
    def _has_access(self, access):
        self.ensure_one()
        if isinstance(self.id, models.NewId):
            return True
        if not self.event_id:
            return False
        try:
            self.event_id.check_access_rights(access)
            self.event_id.check_access_rule(access)
            return True
        except AccessError:
            return False

    @api.depends_context('uid')
    @api.depends('event_id')
    def _compute_access(self):
        for slot in self:
            slot.can_read_private = slot.is_public or slot._has_access('read')
            slot.can_write = slot._has_access('write')

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
                'mo': timeslot.event_id.mo,
                'tu': timeslot.event_id.tu,
                'we': timeslot.event_id.we,
                'th': timeslot.event_id.th,
                'fr': timeslot.event_id.fr,
                'sa': timeslot.event_id.sa,
                'su': timeslot.event_id.su,
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
                'mo': timeslot.mo,
                'tu': timeslot.tu,
                'we': timeslot.we,
                'th': timeslot.th,
                'fr': timeslot.fr,
                'sa': timeslot.sa,
                'su': timeslot.su,
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
        for slot in self:
            slot.name = slot.event_id.name if slot.can_read_private else _('Busy')

    def _inverse_name(self):
        for slot in self:
            slot.event_id.name = slot.name

    @api.depends('event_id.note')
    @api.depends_context('uid')
    def _compute_note(self):
        for slot in self:
            slot.note = slot.can_read_private and slot.event_id.note

    def _inverse_note(self):
        for slot in self:
            slot.event_id.note = slot.note

    @api.depends('partner_ids')
    def _compute_attendee_ids(self):
        for slot in self:
            need_to_add = slot.partner_id + slot.partner_ids._origin - slot.attendee_ids.partner_id
            if need_to_add:
                slot.attendee_ids = [Command.create(
                    {'partner_id': partner.id, 'state': 'yes' if partner == slot.partner_id else 'maybe'}
                ) for partner in need_to_add]

    @api.depends('event_id.tag_ids')
    @api.depends_context('uid')
    def _compute_tag_ids(self):
        for slot in self:
            slot.tag_ids = slot.can_read_private and slot.event_id.tag_ids

    def _inverse_tag_ids(self):
        for slot in self:
            slot.event_id.tag_ids = slot.tag_ids

    def mass_delete(self, update_policy):
        self.ensure_one()
        if not self.can_write:
            raise AccessError(_("You don't have access to delete this timeslot."))
        if update_policy == "all":
            return self.event_id.unlink()
        self.event_id.break_after(self).unlink()

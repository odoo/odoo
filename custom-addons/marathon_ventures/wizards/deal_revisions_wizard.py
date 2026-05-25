# -*- coding: utf-8 -*-
"""Deal Revisions wizard — SF Workflows 3-11 (LTC, Rate, Extend, Frequency, Test,
Cap, Daypart, Hiatus, Max Per Day).

UI choice (per user decision): server-side rendering first. The SF interface is a
line × week grid with click-action cells; we approximate that with one Odoo
notebook tab per revision action, each showing the deal's schedules in a list,
filtered by start-week, with per-tab input fields and an Update button.
"""
from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class MvDealRevisionWizard(models.TransientModel):
    _name = 'mv.deal.revision.wizard'
    _description = 'Deal Revisions'

    # ------------------------------------------------------------------
    # Deal context (loaded from context['active_id'] or button)
    # ------------------------------------------------------------------
    deal_id = fields.Many2one(
        comodel_name='mv.deal',
        string='Deal',
        required=True,
        ondelete='cascade',
    )
    # Read-only deal info echoed at the top (matches SF "Deal Description" header)
    deal_program = fields.Many2one(related='deal_id.program', string='Program', readonly=True)
    deal_brand = fields.Many2one(related='deal_id.brands', string='Brand', readonly=True)
    deal_advertiser = fields.Char(related='deal_id.advertiser', string='Advertiser', readonly=True)
    deal_contact = fields.Many2one(related='deal_id.contact', string='Buyer', readonly=True)
    deal_campaign = fields.Char(related='deal_id.campaign', string='Campaign', readonly=True)
    deal_network_number = fields.Char(related='deal_id.network_deal_number', string='Network Deal #', readonly=True)
    deal_length = fields.Selection(related='deal_id.length', string='Length', readonly=True)
    deal_total_units = fields.Float(related='deal_id.total_booked_units', string='Total Booked Units', readonly=True)
    deal_total_dollars = fields.Monetary(related='deal_id.total_booked_dollars', string='Total Booked Dollars', readonly=True)
    currency_id = fields.Many2one(related='deal_id.currency_id', readonly=True)

    # ------------------------------------------------------------------
    # Schedule selection (the "lines" in the SF wizard)
    # ------------------------------------------------------------------
    available_schedule_ids = fields.Many2many(
        comodel_name='mv.schedules',
        relation='mv_drw_avail_rel',
        column1='wizard_id',
        column2='schedule_id',
        string='Available Schedules',
        compute='_compute_available_schedules',
    )
    selected_schedule_ids = fields.Many2many(
        comodel_name='mv.schedules',
        relation='mv_drw_selected_rel',
        column1='wizard_id',
        column2='schedule_id',
        string='Selected Schedules',
        help='Pick the schedule lines this revision applies to. Empty = the whole deal.',
    )
    start_week = fields.Date(
        string='Start Week (Monday)',
        help='The first Monday from which the revision takes effect. All weeks ON or AFTER this date are affected.',
    )

    # Tab-specific inputs ---------------------------------------------
    ltc_date = fields.Date(string='LTC Date')

    new_rate = fields.Float(string='New Rate', digits=(17, 2))

    extend_to_week = fields.Date(string='Extend Through Week (Monday)')

    new_units_available = fields.Float(string='New Units Available', digits=(17, 1))

    test_week = fields.Date(string='Test Week (Monday)')
    test_value = fields.Boolean(string='Mark as Test', default=True,
                                help='If unchecked, the Update action *removes* the Test flag on the selected week.')

    new_cap = fields.Selection(
        selection=lambda s: list(s.env['mv.schedules']._fields['cap'].selection),
        string='New Cap',
    )

    new_days_allowed_ids = fields.Many2many(
        comodel_name='mv.days_allowed.tag',
        relation='mv_drw_days_rel',
        string='New Days Allowed',
    )
    new_start_time = fields.Selection(
        selection=lambda s: list(s.env['mv.schedules']._fields['start_time'].selection),
        string='New Start Time',
    )
    new_end_time = fields.Selection(
        selection=lambda s: list(s.env['mv.schedules']._fields['end_time'].selection),
        string='New End Time',
    )

    hiatus_start_date = fields.Date(string='Hiatus Start Date')
    hiatus_end_date = fields.Date(string='Hiatus End Date')
    hiatus_time_before = fields.Selection(
        selection=lambda s: list(s.env['mv.schedules']._fields['start_time'].selection),
        string='Hiatus Time Before',
        help='If set, hiatus only those schedules whose Start Time is before this hour.',
    )
    hiatus_time_after = fields.Selection(
        selection=lambda s: list(s.env['mv.schedules']._fields['end_time'].selection),
        string='Hiatus Time After',
        help='If set, hiatus only those schedules whose End Time is after this hour.',
    )

    new_max_per_day = fields.Integer(string='New Max Per Day')

    # Tracks which tab the user is currently on (drives the single Update button)
    active_tab = fields.Selection(
        selection=[
            ('ltc', 'LTC'),
            ('rate', 'Rate'),
            ('extend', 'Extend'),
            ('frequency', 'Frequency'),
            ('test', 'Test'),
            ('cap', 'Cap'),
            ('daypart', 'Daypart'),
            ('hiatus', 'Hiatus'),
            ('max_per_day', 'Max Per Day'),
        ],
        default='ltc',
        string='Active Tab',
    )

    def action_apply_active_tab(self):
        """Dispatch to the per-tab apply method based on active_tab."""
        self.ensure_one()
        method = 'action_apply_' + (self.active_tab or 'ltc')
        if hasattr(self, method):
            return getattr(self, method)()
        from odoo.exceptions import UserError
        raise UserError('No action defined for tab %s' % self.active_tab)

    # ------------------------------------------------------------------
    # Computed lists
    # ------------------------------------------------------------------
    @api.depends('deal_id')
    def _compute_available_schedules(self):
        for w in self:
            if w.deal_id:
                w.available_schedule_ids = w.deal_id.schedule_ids
            else:
                w.available_schedule_ids = self.env['mv.schedules']

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _affected_schedules(self, require_start_week=True):
        """Return the schedules this revision will touch."""
        self.ensure_one()
        if require_start_week and not self.start_week:
            raise UserError(_("Please select a Start Week (must be a Monday)."))
        if self.start_week and self.start_week.weekday() != 0:
            raise UserError(_("Start Week must be a Monday (you entered %s)") % self.start_week)
        scope = self.selected_schedule_ids or self.available_schedule_ids
        if not scope:
            raise UserError(_("No schedules selected and the deal has none — nothing to revise."))
        if require_start_week:
            scope = scope.filtered(lambda s: s.week and s.week >= self.start_week)
        if not scope:
            raise UserError(_("No schedules match the filter (start week %s).") % self.start_week)
        return scope

    def _close(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _('Deal — %s') % self.deal_id.display_name,
            'res_model': 'mv.deal',
            'view_mode': 'form',
            'res_id': self.deal_id.id,
            'target': 'current',
        }

    # ------------------------------------------------------------------
    # Tab actions  (one per tab, matching SF "Update" button per tab)
    # ------------------------------------------------------------------
    # 1) LTC  ----------------------------------------------------------
    def action_apply_ltc(self):
        self.ensure_one()
        if not self.ltc_date:
            raise UserError(_("Enter the LTC Date before clicking Update."))
        # In SF: keep current-week units (may have aired), cancel weeks strictly after LTC.
        scope = self._affected_schedules(require_start_week=False)
        ltc = self.ltc_date
        for s in scope:
            if s.week and s.week > ltc:
                s.status = 'canceled'
        self.deal_id.message_post(body=_("LTC %s applied — %d future schedules cancelled.") % (ltc, len(scope.filtered(lambda x: x.status == 'canceled'))))
        return self._close()

    # 2) Rate  ---------------------------------------------------------
    def action_apply_rate(self):
        self.ensure_one()
        if self.new_rate is None:
            raise UserError(_("Enter a New Rate."))
        if self.new_rate < 0:
            raise UserError(_("Rate cannot be negative."))
        scope = self._affected_schedules()
        scope.write({'rate': self.new_rate})
        self.deal_id.message_post(body=_("Rate set to %s on %d schedules (week >= %s).") % (self.new_rate, len(scope), self.start_week))
        return self._close()

    # 3) Extend  -------------------------------------------------------
    def action_apply_extend(self):
        self.ensure_one()
        if not self.extend_to_week:
            raise UserError(_("Enter the Last Monday of the extension."))
        if self.extend_to_week.weekday() != 0:
            raise UserError(_("Extend-To week must be a Monday."))
        scope = self.selected_schedule_ids or self.available_schedule_ids
        if not scope:
            raise UserError(_("Pick at least one source schedule to extend."))

        Schedule = self.env['mv.schedules']
        created = 0
        for s in scope:
            if not s.week:
                continue
            # find the latest week already booked for this "line" (same daypart/days/times/rate as s)
            line_schedules = scope.filtered(lambda x: (
                x.daypart == s.daypart and
                x.start_time == s.start_time and
                x.end_time == s.end_time and
                set(x.days_allowed.ids) == set(s.days_allowed.ids) and
                x.rate == s.rate
            ))
            last_week = max(line_schedules.mapped('week'))
            if last_week >= self.extend_to_week:
                continue
            cursor = last_week + timedelta(days=7)
            while cursor <= self.extend_to_week:
                copy_vals = {
                    'deal_parent': s.deal_parent.id,
                    'week': cursor,
                    'rate': s.rate,
                    'units_available': s.units_available,
                    'networks': s.networks,
                    'cap': s.cap,
                    'max_per_day': s.max_per_day,
                    'priority': s.priority,
                    'special': s.special if s.special else False,
                    'start_time': s.start_time,
                    'end_time': s.end_time,
                    'test': False,  # extensions reset Test
                    'days_allowed': [(6, 0, s.days_allowed.ids)],
                    'status': 'sold',
                }
                Schedule.create(copy_vals)
                created += 1
                cursor += timedelta(days=7)
        self.deal_id.message_post(body=_("Extend applied through %s — %d new schedules created.") % (self.extend_to_week, created))
        return self._close()

    # 4) Frequency  ---------------------------------------------------
    def action_apply_frequency(self):
        self.ensure_one()
        if self.new_units_available is None or self.new_units_available < 0:
            raise UserError(_("Enter a non-negative Units Available value."))
        scope = self._affected_schedules()
        scope.write({'units_available': self.new_units_available})
        self.deal_id.message_post(body=_("Frequency set to %s on %d schedules (week >= %s).") % (self.new_units_available, len(scope), self.start_week))
        return self._close()

    # 5) Test  --------------------------------------------------------
    def action_apply_test(self):
        self.ensure_one()
        if not self.test_week:
            raise UserError(_("Pick the single Test Week."))
        if self.test_week.weekday() != 0:
            raise UserError(_("Test Week must be a Monday."))
        scope = (self.selected_schedule_ids or self.available_schedule_ids).filtered(lambda s: s.week == self.test_week)
        if not scope:
            raise UserError(_("No schedules match week %s.") % self.test_week)
        scope.write({'test': bool(self.test_value)})
        self.deal_id.message_post(body=_("Test=%s applied to %d schedules in week %s.") % (self.test_value, len(scope), self.test_week))
        return self._close()

    # 6) Cap  ---------------------------------------------------------
    def action_apply_cap(self):
        self.ensure_one()
        if not self.new_cap:
            raise UserError(_("Pick the New Cap value."))
        scope = self._affected_schedules()
        scope.write({'cap': self.new_cap})
        self.deal_id.message_post(body=_("Cap set to %s on %d schedules (week >= %s).") % (self.new_cap, len(scope), self.start_week))
        return self._close()

    # 7) Daypart  -----------------------------------------------------
    @api.model
    def _time_selection_to_hour(self, key):
        """Convert SF time picklist key like 'v_09_30a' / 'v_06_00p' to float hour 0..24."""
        if not key:
            return None
        try:
            # key like 'v_09_30a' or 'v_12_00p'
            _, hh, mm_ap = key.split('_', 2)
            h = int(hh)
            mm = int(mm_ap[:2])
            ap = mm_ap[2]
            if ap == 'a':
                if h == 12: h = 0
            elif ap == 'p':
                if h != 12: h += 12
            return h + mm / 60.0
        except Exception:
            return None

    def action_apply_daypart(self):
        self.ensure_one()
        scope = self._affected_schedules()
        update_vals = {}
        # daypart is computed on mv.schedules — so we cannot write it directly.
        # Days allowed / Start time / End time are editable.
        if self.new_days_allowed_ids:
            update_vals['days_allowed'] = [(6, 0, self.new_days_allowed_ids.ids)]
        if self.new_start_time:
            update_vals['start_time'] = self.new_start_time
        if self.new_end_time:
            update_vals['end_time'] = self.new_end_time
        if not update_vals:
            raise UserError(_("Set Days Allowed and/or Start/End Time before clicking Update."))
        scope.write(update_vals)
        self.deal_id.message_post(body=_("Daypart updated on %d schedules (week >= %s).") % (len(scope), self.start_week))
        return self._close()

    # 8) Hiatus  ------------------------------------------------------
    def action_apply_hiatus(self):
        self.ensure_one()
        if not (self.hiatus_start_date and self.hiatus_end_date):
            raise UserError(_("Pick both Hiatus Start Date and Hiatus End Date."))
        if self.hiatus_end_date < self.hiatus_start_date:
            raise UserError(_("Hiatus End Date must be on or after Start Date."))
        # Map: weekday name → Mon/Tue/.../Sun
        WD = {0: 'Mon', 1: 'Tue', 2: 'Wed', 3: 'Thu', 4: 'Fri', 5: 'Sat', 6: 'Sun'}
        Tag = self.env['mv.days_allowed.tag']
        scope = self.selected_schedule_ids or self.available_schedule_ids
        affected_count = 0
        for s in scope:
            if not s.week:
                continue
            # determine the set of hiatus weekdays that overlap this schedule's week
            week_start = s.week
            week_end = s.week + timedelta(days=6)
            overlap_start = max(week_start, self.hiatus_start_date)
            overlap_end = min(week_end, self.hiatus_end_date)
            if overlap_end < overlap_start:
                continue
            hiatus_weekdays = set()
            d = overlap_start
            while d <= overlap_end:
                hiatus_weekdays.add(WD[d.weekday()])
                d += timedelta(days=1)

            # Apply time-before / time-after filter if set (compare in hour-floats)
            if self.hiatus_time_before:
                cutoff = self._time_selection_to_hour(self.hiatus_time_before)
                sched_start = self._time_selection_to_hour(s.start_time)
                if cutoff is not None and sched_start is not None and sched_start >= cutoff:
                    continue
            if self.hiatus_time_after:
                cutoff = self._time_selection_to_hour(self.hiatus_time_after)
                sched_end = self._time_selection_to_hour(s.end_time)
                if cutoff is not None and sched_end is not None and sched_end <= cutoff:
                    continue

            # Remove the matching weekday tags from days_allowed
            to_remove = s.days_allowed.filtered(lambda t: (t.code or t.name) in hiatus_weekdays)
            if to_remove:
                s.days_allowed = [(3, t.id) for t in to_remove]
                affected_count += 1
        self.deal_id.message_post(body=_("Hiatus %s – %s applied to %d schedules.") % (self.hiatus_start_date, self.hiatus_end_date, affected_count))
        return self._close()

    # 9) Max Per Day  -------------------------------------------------
    def action_apply_max_per_day(self):
        self.ensure_one()
        if self.new_max_per_day is None or self.new_max_per_day < 0:
            raise UserError(_("Max Per Day must be a non-negative integer."))
        scope = self._affected_schedules()
        scope.write({'max_per_day': self.new_max_per_day})
        self.deal_id.message_post(body=_("Max Per Day set to %s on %d schedules (week >= %s).") % (self.new_max_per_day, len(scope), self.start_week))
        return self._close()

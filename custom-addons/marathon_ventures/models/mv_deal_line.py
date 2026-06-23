# -*- coding: utf-8 -*-
"""mv.deal_line - Schedule template row owned by a Deal.

One Deal Line == one daypart configuration spanning a date range.
The Units Grid OWL widget shows Deal Lines as rows and weeks as columns;
each cell is a units_available value coming from the linked
mv.schedules records (deal_line_id). On save, the parent Deal Line's
rate / days_allowed / start_time / end_time are copied onto the
freshly-created or updated Schedule rows.
"""
from odoo import models, fields, api


DAYPART_SELECTION = [
    ('early_morning', 'Early Morning'),
    ('day',           'Day'),
    ('prime',         'Prime'),
    ('late_fringe',   'Late Fringe'),
    ('overnight',     'Overnight'),
    # `custom` is auto-selected when the planner enters a start/end
    # time pair that doesn't match any of the standard daypart ranges
    # above. No default range / default times - the planner's chosen
    # start_time and end_time are the source of truth.
    ('custom',        'Custom'),
]

DAYPART_DEFAULT_RANGE = {
    'early_morning': '6a - 9a',
    'day':           '9a - 6p',
    'prime':         '6p - 12a',
    'late_fringe':   '12a - 2a',
    'overnight':     '2a - 6a',
    'custom':        '',
}

# Map daypart -> (start_time picklist key, end_time picklist key) on
# mv.schedules. These keys must exist in the SF Selection lists for
# mv.schedules.start_time / .end_time.
DAYPART_DEFAULT_TIMES = {
    'early_morning': ('v_06_00a', 'v_09_00a'),
    'day':           ('v_09_00a', 'v_06_00p'),
    'prime':         ('v_06_00p', 'v_12_00a'),
    'late_fringe':   ('v_12_00a', 'v_02_00a'),
    'overnight':     ('v_02_00a', 'v_06_00a'),
}

# Boolean field name -> seed tag xmlid for the days_allowed mirror.
DAY_BOOL_TO_TAG_XMLID = [
    ('day_mon', 'marathon_ventures.days_allowed_mon'),
    ('day_tue', 'marathon_ventures.days_allowed_tue'),
    ('day_wed', 'marathon_ventures.days_allowed_wed'),
    ('day_thu', 'marathon_ventures.days_allowed_thu'),
    ('day_fri', 'marathon_ventures.days_allowed_fri'),
    ('day_sat', 'marathon_ventures.days_allowed_sat'),
    ('day_sun', 'marathon_ventures.days_allowed_sun'),
]


def _times_selection(self):
    """Reuse mv.schedules.start_time's full 48-slot picklist so the Deal
    Line uses the exact same values the schedule will store."""
    return self.env['mv.schedules']._fields['start_time'].selection


class MvDealLine(models.Model):
    _name = 'mv.deal_line'
    _description = 'Deal Line (Units Grid Row)'
    _order = 'deal_id, daypart, run_start'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string='Display Name',
        compute='_compute_name',
        store=True,
    )
    deal_id = fields.Many2one(
        comodel_name='mv.deal',
        string='Deal',
        required=True,
        ondelete='cascade',
        index=True,
    )
    currency_id = fields.Many2one(
        related='deal_id.currency_id',
        store=True,
        readonly=True,
    )

    daypart = fields.Selection(
        selection=DAYPART_SELECTION,
        string='Daypart',
        required=True,
        default='early_morning',
        tracking=True,
    )
    time_range = fields.Char(
        string='Time Range',
        compute='_compute_time_range',
        store=True,
        readonly=False,
    )

    # Editable time picklists - mirrors mv.schedules' Selection.
    start_time = fields.Selection(
        selection=_times_selection,
        string='Start Time',
    )
    end_time = fields.Selection(
        selection=_times_selection,
        string='End Time',
    )

    # Per-row Max Per Day cap. Propagated to every child Schedule on
    # save (see schedule_inherit_vals below).
    max_per_day = fields.Integer(
        string='Max Per Day',
        help='Upper bound on spots per day. Applied to every Schedule '
             'created from / linked to this Deal Line when the planner '
             'clicks Save in the Units Grid.',
    )

    # Days of week toggles - blue/active when True per the mockup.
    day_mon = fields.Boolean(string='M', default=True)
    day_tue = fields.Boolean(string='T', default=True)
    day_wed = fields.Boolean(string='W', default=True)
    day_thu = fields.Boolean(string='T', default=True)
    day_fri = fields.Boolean(string='F', default=True)
    day_sat = fields.Boolean(string='S', default=False)
    day_sun = fields.Boolean(string='S', default=False)

    # M2M mirror of the day Booleans - kept in sync via compute so it
    # can be propagated verbatim onto child Schedule rows.
    days_allowed = fields.Many2many(
        comodel_name='mv.days_allowed.tag',
        relation='mv_deal_line_days_allowed_rel',
        string='Days Allowed',
        compute='_compute_days_allowed',
        store=True,
    )

    rate = fields.Monetary(
        string='Rate (per spot)',
        currency_field='currency_id',
        required=True,
        default=0.0,
    )
    run_start = fields.Date(string='Run Start', required=True)
    run_end   = fields.Date(string='Run End',   required=True)

    schedule_ids = fields.One2many(
        comodel_name='mv.schedules',
        inverse_name='deal_line_id',
        string='Schedules',
    )
    total_spots = fields.Float(
        string='Total Spots',
        compute='_compute_totals', store=True, digits=(17, 1),
    )
    total_revenue = fields.Monetary(
        string='Total Revenue',
        compute='_compute_totals', store=True, currency_field='currency_id',
    )

    # --- Computes ------------------------------------------------------
    @api.depends('daypart', 'run_start', 'run_end')
    def _compute_name(self):
        labels = dict(DAYPART_SELECTION)
        for rec in self:
            label = labels.get(rec.daypart, rec.daypart or 'New')
            if rec.run_start and rec.run_end:
                rec.name = "%s (%s -> %s)" % (label, rec.run_start, rec.run_end)
            else:
                rec.name = label

    @api.depends('daypart')
    def _compute_time_range(self):
        for rec in self:
            if not rec.time_range:
                rec.time_range = DAYPART_DEFAULT_RANGE.get(rec.daypart, '')

    @api.depends('day_mon', 'day_tue', 'day_wed', 'day_thu',
                 'day_fri', 'day_sat', 'day_sun')
    def _compute_days_allowed(self):
        for rec in self:
            tag_ids = []
            for fname, xmlid in DAY_BOOL_TO_TAG_XMLID:
                if getattr(rec, fname):
                    tag = rec.env.ref(xmlid, raise_if_not_found=False)
                    if tag:
                        tag_ids.append(tag.id)
            rec.days_allowed = [(6, 0, tag_ids)]

    @api.depends('schedule_ids', 'schedule_ids.units_available',
                 'schedule_ids.total_dollars', 'schedule_ids.status')
    def _compute_totals(self):
        for rec in self:
            live = rec.schedule_ids.filtered(lambda s: s.status != 'canceled')
            rec.total_spots = sum(live.mapped('units_available') or [0.0])
            rec.total_revenue = sum(live.mapped('total_dollars') or [0.0])

    @api.onchange('daypart')
    def _onchange_daypart_default_times(self):
        for rec in self:
            defaults = DAYPART_DEFAULT_TIMES.get(rec.daypart)
            if defaults and not rec.start_time:
                rec.start_time = defaults[0]
            if defaults and not rec.end_time:
                rec.end_time = defaults[1]

    def days_mask(self):
        self.ensure_one()
        return [self.day_mon, self.day_tue, self.day_wed, self.day_thu,
                self.day_fri, self.day_sat, self.day_sun]

    def schedule_inherit_vals(self):
        """Fields the child Schedule should inherit from this Deal Line.
        Used by phase10_units_grid_rpc.save_units_grid when creating /
        updating a Schedule from a grid cell."""
        self.ensure_one()
        defaults = DAYPART_DEFAULT_TIMES.get(self.daypart, (False, False))
        return {
            'rate':         self.rate,
            'start_time':   self.start_time or defaults[0] or False,
            'end_time':     self.end_time   or defaults[1] or False,
            'days_allowed': [(6, 0, self.days_allowed.ids)],
            'max_per_day':  self.max_per_day or 0,
        }

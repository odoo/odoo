# -*- coding: utf-8 -*-
"""Phase 16 - Program-Specific Dayparts.

Each mv.programs can optionally define its own list of dayparts
(name + start_time + end_time). When a Deal's program has any custom
dayparts configured, the Units Report and Capping Report use them for
classification and display. When the program has none, the reports
fall back to the hard-coded DAYPART_DEFAULT_TIMES / DAYPART_LABELS
from phase10_units_grid_rpc so existing deals behave exactly as
before (backward compatible).

Only the dictionaries lookups in load_units_grid / load_capping_grid
consult this list - the schedule itself still stores start_time /
end_time as Selection values, and the signature grouping is
unchanged.
"""
from odoo import models, fields, api


# Selection tuples for start_time / end_time. Kept in sync with
# mv.schedules; centralised here so both fields share one list.
_TIME_SELECTION = [
    ('v_01_00a', '01:00A'), ('v_01_30a', '01:30A'),
    ('v_02_00a', '02:00A'), ('v_02_30a', '02:30A'),
    ('v_03_00a', '03:00A'), ('v_03_30a', '03:30A'),
    ('v_04_00a', '04:00A'), ('v_04_30a', '04:30A'),
    ('v_05_00a', '05:00A'), ('v_05_30a', '05:30A'),
    ('v_06_00a', '06:00A'), ('v_06_30a', '06:30A'),
    ('v_07_00a', '07:00A'), ('v_07_30a', '07:30A'),
    ('v_08_00a', '08:00A'), ('v_08_30a', '08:30A'),
    ('v_09_00a', '09:00A'), ('v_09_30a', '09:30A'),
    ('v_10_00a', '10:00A'), ('v_10_30a', '10:30A'),
    ('v_11_00a', '11:00A'), ('v_11_30a', '11:30A'),
    ('v_12_00p', '12:00P'), ('v_12_30p', '12:30P'),
    ('v_01_00p', '01:00P'), ('v_01_30p', '01:30P'),
    ('v_02_00p', '02:00P'), ('v_02_30p', '02:30P'),
    ('v_03_00p', '03:00P'), ('v_03_30p', '03:30P'),
    ('v_04_00p', '04:00P'), ('v_04_30p', '04:30P'),
    ('v_05_00p', '05:00P'), ('v_05_30p', '05:30P'),
    ('v_06_00p', '06:00P'), ('v_06_30p', '06:30P'),
    ('v_07_00p', '07:00P'), ('v_07_30p', '07:30P'),
    ('v_08_00p', '08:00P'), ('v_08_30p', '08:30P'),
    ('v_09_00p', '09:00P'), ('v_09_30p', '09:30P'),
    ('v_10_00p', '10:00P'), ('v_10_30p', '10:30P'),
    ('v_11_00p', '11:00P'), ('v_11_30p', '11:30P'),
    ('v_12_00a', '12:00A'), ('v_12_30a', '12:30A'),
]


class MvProgramDaypart(models.Model):
    _name = 'mv.program.daypart'
    _description = 'Program Daypart'
    _order = 'sequence, id'

    sequence = fields.Integer(default=10)
    program_id = fields.Many2one(
        'mv.programs', string='Program',
        required=True, ondelete='cascade', index=True,
    )
    name = fields.Char(string='Daypart Name', required=True)
    start_time = fields.Selection(_TIME_SELECTION, string='Start Time')
    end_time = fields.Selection(_TIME_SELECTION, string='End Time')

    # Auto-derived "6a - 9a"-style label from the picked start/end.
    # Stored so list views + reports can filter/group by it without
    # recomputing on every read.
    time_range = fields.Char(
        string='Time Range',
        compute='_compute_time_range', store=True,
    )

    # Days of the week this daypart runs on. Same Many2many target as
    # mv.schedules.days_allowed so the codes line up 1:1 - the Units
    # Grid can copy this straight onto a row when the planner picks
    # this daypart. Default M-F set via _default_days_allowed_ids.
    days_allowed_ids = fields.Many2many(
        comodel_name='mv.days_allowed.tag',
        relation='mv_program_daypart_days_allowed_rel',
        column1='daypart_id', column2='tag_id',
        string='Days Allowed',
        default=lambda self: self._default_days_allowed_ids(),
    )

    @api.model
    def _default_days_allowed_ids(self):
        """Mon..Fri as the sensible business default. Falls back to
        an empty set if the seed data hasn't loaded yet (shouldn't
        happen post-install but guard anyway)."""
        Tag = self.env['mv.days_allowed.tag']
        try:
            return [(6, 0, Tag.search([
                ('code', 'in', ['Mon', 'Tue', 'Wed', 'Thu', 'Fri']),
            ]).ids)]
        except Exception:
            return [(6, 0, [])]

    _sql_constraints = [
        (
            'name_program_uniq',
            'unique(program_id, name)',
            'Daypart name must be unique per program.',
        ),
    ]

    @api.depends('start_time', 'end_time')
    def _compute_time_range(self):
        sel = dict(_TIME_SELECTION)
        for rec in self:
            s = (sel.get(rec.start_time) or '').lower() if rec.start_time else ''
            e = (sel.get(rec.end_time)   or '').lower() if rec.end_time   else ''
            # Compact "06:00a" -> "6a" for readability.
            s = _shorten_time_label(s)
            e = _shorten_time_label(e)
            if s and e:
                rec.time_range = '%s - %s' % (s, e)
            else:
                rec.time_range = s or e or ''


def _shorten_time_label(lbl):
    """'09:00a' -> '9a', '12:30p' -> '12:30p', ''-> ''."""
    if not lbl:
        return ''
    # split into HH:MM and the a/p suffix
    body = lbl[:-1]  # drop last char (a/p)
    suf = lbl[-1:]
    hh, _, mm = body.partition(':')
    hh = hh.lstrip('0') or '0'
    if mm and mm != '00':
        return '%s:%s%s' % (hh, mm, suf)
    return '%s%s' % (hh, suf)


class MvProgramsInheritDaypart(models.Model):
    _name = 'mv.programs'
    _inherit = 'mv.programs'

    daypart_ids = fields.One2many(
        'mv.program.daypart', 'program_id',
        string='Dayparts',
    )

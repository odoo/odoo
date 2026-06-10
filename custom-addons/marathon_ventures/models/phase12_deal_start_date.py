# -*- coding: utf-8 -*-
"""Phase 12 - Deal-level Start Date for the Units / Capping Reports.

* `units_start_date` is always snapped to the Monday of the picked
  week (onchange + write/create override).
* Week columns include only Mondays whose Sunday (Mon + 6 days) is
  still inside the same calendar quarter as the start date - any
  Monday whose week spills into the next quarter is excluded.
"""
from datetime import date, timedelta
from odoo import models, fields, api


def _snap_to_monday(d):
    """Walk a date back to the Monday of that ISO week."""
    if not d:
        return d
    while d.weekday() != 0:
        d -= timedelta(days=1)
    return d


def _last_day_of_quarter(d):
    """Return the calendar last day of the quarter containing `d`."""
    q_idx = (d.month - 1) // 3                # 0..3
    last_month_in_q = q_idx * 3 + 3           # 3, 6, 9, 12
    if last_month_in_q == 12:
        next_q_first = date(d.year + 1, 1, 1)
    else:
        next_q_first = date(d.year, last_month_in_q + 1, 1)
    return next_q_first - timedelta(days=1)


def mondays_for_start_date(start_date):
    """Return list[date] of Mondays such that the FULL week (Mon..Sun)
    sits inside the same calendar quarter as `start_date`."""
    if not start_date:
        start_date = date.today()
    first_monday = _snap_to_monday(start_date)
    last_day_of_q = _last_day_of_quarter(start_date)
    mondays = []
    cur = first_monday
    while cur <= last_day_of_q:
        week_sunday = cur + timedelta(days=6)
        if week_sunday <= last_day_of_q:
            mondays.append(cur)
        cur += timedelta(days=7)
    return mondays


class MvDealUnitsStartDate(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    units_start_date = fields.Date(
        string='Deal Start Date',
        default=fields.Date.context_today,
        help='Drives the Units / Capping Report week columns. Columns '
             'run from the Monday of this date through the last Monday '
             'whose week ends within the same calendar quarter.',
    )

    # ------------------------------------------------------------------
    # Always snap units_start_date to Monday on save / onchange so the
    # field state always matches what the OWL grid expects.
    # ------------------------------------------------------------------
    @api.onchange('units_start_date')
    def _onchange_units_start_date_snap_monday(self):
        for rec in self:
            if rec.units_start_date and rec.units_start_date.weekday() != 0:
                rec.units_start_date = _snap_to_monday(rec.units_start_date)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('units_start_date'):
                raw = vals['units_start_date']
                if isinstance(raw, str):
                    raw = fields.Date.from_string(raw)
                if raw and raw.weekday() != 0:
                    vals['units_start_date'] = _snap_to_monday(raw)
        return super().create(vals_list)

    def write(self, vals):
        if vals.get('units_start_date'):
            raw = vals['units_start_date']
            if isinstance(raw, str):
                raw = fields.Date.from_string(raw)
            if raw and raw.weekday() != 0:
                vals['units_start_date'] = _snap_to_monday(raw)
        return super().write(vals)

    def units_grid_weeks(self):
        self.ensure_one()
        return mondays_for_start_date(self.units_start_date or date.today())

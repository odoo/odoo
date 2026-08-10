# -*- coding: utf-8 -*-
"""Phase 12 - Deal-level Start Date for the Units / Capping Reports.

* `units_start_date` is always snapped to the Monday of the picked
  week (onchange + write/create override).
* Week columns include only Mondays whose Sunday (Mon + 6 days) is
  still inside the same BROADCAST quarter as the start date - any
  Monday whose week spills into the next broadcast quarter is excluded.
  A broadcast quarter starts on the Monday of the calendar week that
  contains the 1st of Jan / Apr / Jul / Oct (so broadcast Q2 2026
  starts Mon March 30, 2026 because April 1, 2026 is a Wednesday).
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


def _broadcast_month_start(year, month):
    """Return the Monday of the calendar week containing the 1st of
    (year, month). That Monday is the first day of the broadcast month.

    Example: April 1, 2026 is a Wednesday, so the broadcast April begins
    on Monday March 30, 2026. This in turn is the first day of the
    broadcast Q2 2026.
    """
    first = date(year, month, 1)
    # weekday(): Monday=0, Sunday=6
    return first - timedelta(days=first.weekday())


def _broadcast_quarter_bounds(d):
    """Return (start_monday, end_sunday) of the BROADCAST quarter
    containing date `d`.

    A broadcast quarter starts at the broadcast month of the first
    calendar month of the quarter (Jan / Apr / Jul / Oct) and ends the
    day before the next broadcast quarter starts.

    Implementation: enumerate every quarter-start in a +/- 1 year window
    and pick the bracket that contains `d`. Naturally handles 53-week
    broadcast years (the bracket will simply be 14 weeks).
    """
    candidates = []
    for y in (d.year - 1, d.year, d.year + 1):
        for m in (1, 4, 7, 10):
            candidates.append(_broadcast_month_start(y, m))
    candidates.sort()
    for i, s in enumerate(candidates):
        next_s = candidates[i + 1] if i + 1 < len(candidates) else None
        if s <= d and (next_s is None or next_s > d):
            if next_s is None:
                # Shouldn't happen with a +/-1y window, but be safe:
                # default to a 13-week bracket.
                return (s, s + timedelta(days=13 * 7 - 1))
            return (s, next_s - timedelta(days=1))
    # Fallback (date is somehow before our earliest candidate):
    return (candidates[0], candidates[1] - timedelta(days=1))


def mondays_for_start_date(start_date):
    """Return list[date] of Mondays from the deal start date through the
    end of the BROADCAST quarter containing that start date. Only Mondays
    whose full Mon..Sun week stays inside the broadcast quarter are
    included.
    """
    if not start_date:
        start_date = date.today()
    first_monday = _snap_to_monday(start_date)
    q_start, q_end = _broadcast_quarter_bounds(first_monday)
    mondays = []
    cur = first_monday
    while cur + timedelta(days=6) <= q_end:
        mondays.append(cur)
        cur += timedelta(days=7)
    return mondays


class MvDealUnitsStartDate(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    units_start_date = fields.Date(
        string='Deal Start Date',
        default=lambda self: _snap_to_monday(
            fields.Date.context_today(self)
        ),
        help='Drives the Units / Capping Report week columns. Columns '
             'run from the Monday of this date through the last Monday '
             'whose week ends within the same broadcast quarter. New '
             'deals default to the Monday of the current week.',
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

# -*- coding: utf-8 -*-
"""Phase 10 - RPC methods backing the Units Grid OWL widget.

Exposed on mv.deal so the front-end can call:
    self.env['mv.deal'].browse(deal_id).load_units_grid()
    self.env['mv.deal'].browse(deal_id).save_units_grid(edits)
"""
from datetime import date, timedelta
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError

# Phase 12: weeks are now derived from the Deal's units_start_date
# (see models/phase12_deal_start_date.py). The old _quarter_mondays
# helper is kept only as a fallback when units_start_date is missing.
from odoo.addons.marathon_ventures.models.phase12_deal_start_date import (
    mondays_for_start_date,
)
from odoo.addons.marathon_ventures.models.mv_deal_line import (
    DAYPART_DEFAULT_TIMES,
)


def _quarter_mondays(today=None):
    """Legacy fallback - returns Mondays from the start of the current
    quarter for 13 weeks. New code uses mondays_for_start_date()."""
    return mondays_for_start_date(today or date.today())


class MvDealUnitsGridRpc(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    # ------------------------------------------------------------------
    # Read: full grid payload for the OWL widget
    # ------------------------------------------------------------------
    def load_units_grid(self):
        """Return the data the front-end needs to render the Units Grid.

        Shape:
            {
              'deal': {'id': 12, 'name': 'D-001', 'program': 'WNBC Morning',
                       'brand': 'Acme', 'advertiser': 'Acme Corp',
                       'account': 'Acme Holdings', 'length': '30',
                       'order_number': '12345'},
              'weeks': ['2026-03-02', '2026-03-09', ...],  # ISO Mondays
              'rows':  [
                 {'id': 5, 'daypart': 'early_morning',
                  'daypart_label': 'Early Morning',
                  'time_range': '6a - 9a',
                  'days_mask': [True,True,True,True,True,False,False],
                  'rate': 85.0, 'run_start': '2026-03-02',
                  'run_end': '2026-04-20',
                  'cells': [
                     {'week': '2026-03-02', 'units': 20, 'state': 'green',
                      'sched_id': 17},
                     ...
                  ],
                  'total_spots': 160, 'total_revenue': 13600.0},
                 ...
              ],
              'grand_total_spots': 304,
              'grand_total_revenue': 29260.0,
              'currency': {'id': 1, 'symbol': '$', 'position': 'before'},
            }
        """
        self.ensure_one()
        # Phase 12: derive the week columns from the deal-level start date
        weeks = mondays_for_start_date(self.units_start_date)
        weeks_iso = [w.isoformat() for w in weeks]

        rows = []
        grand_spots = 0.0
        grand_rev = 0.0
        grand_cancelled = 0.0
        for dl in self.env['mv.deal_line'].search([('deal_id', '=', self.id)]):
            # Index schedules by week. A week can carry up to TWO
            # schedules now: an active one (status != 'canceled') and a
            # cancelled one (status == 'canceled'). They render as two
            # separate UI elements in the same cell: the active is the
            # editable input, the cancelled is the small red label below.
            active_by_week = {}     # week_iso -> sched (status != canceled)
            cancelled_by_week = {}  # week_iso -> [sched, sched, ...]
            for sched in dl.schedule_ids:
                if not sched.week:
                    continue
                w = sched.week.isoformat()
                if (sched.status or '') == 'canceled':
                    cancelled_by_week.setdefault(w, []).append(sched)
                else:
                    # If two non-canceled schedules ever exist for the
                    # same week, keep the most recent (highest id) as
                    # the active one; the rest fall back to the
                    # cancelled bucket so they show up somewhere.
                    prev = active_by_week.get(w)
                    if prev is None or sched.id > prev.id:
                        if prev is not None:
                            cancelled_by_week.setdefault(w, []).append(prev)
                        active_by_week[w] = sched
                    else:
                        cancelled_by_week.setdefault(w, []).append(sched)

            cells = []
            row_cancelled_units = 0.0
            for w_iso, w_dt in zip(weeks_iso, weeks):
                active = active_by_week.get(w_iso)
                cancelled_list = cancelled_by_week.get(w_iso) or []
                cancelled_units = sum(
                    (s.units_available or 0.0) for s in cancelled_list
                )
                row_cancelled_units += cancelled_units

                # Active-side state (the editable input)
                if not active or not active.units_available:
                    state = 'dashed'
                    active_units = 0
                    active_id = active.id if active else False
                else:
                    cap = active.cap or 'uncapped'
                    state = 'green'
                    if cap == 'ghost':
                        state = 'gray'
                    elif cap in ('v_50', 'v_50_2', 'v_80', 'v_80_in_ov',
                                 'v_1_2_in_pr_and_1_2_in_ov'):
                        state = 'amber'
                    active_units = active.units_available
                    active_id = active.id

                cells.append({
                    'week': w_iso,
                    'units': active_units,
                    'state': state,
                    'sched_id': active_id,
                    'cancelled_units': cancelled_units,
                    'cancelled_sched_ids': [s.id for s in cancelled_list],
                })

            row = {
                'id': dl.id,
                'daypart': dl.daypart,
                'daypart_label': dict(dl._fields['daypart'].selection).get(
                    dl.daypart, dl.daypart or '',
                ),
                'time_range': dl.time_range or '',
                'start_time': dl.start_time or False,
                'end_time':   dl.end_time   or False,
                'days_mask': dl.days_mask(),
                'rate': dl.rate,
                'max_per_day': dl.max_per_day or 0,
                'run_start': dl.run_start.isoformat() if dl.run_start else None,
                'run_end':   dl.run_end.isoformat()   if dl.run_end   else None,
                'cells': cells,
                'total_spots': dl.total_spots,
                'total_revenue': dl.total_revenue,
                'total_cancelled': row_cancelled_units,
            }
            rows.append(row)
            grand_spots += dl.total_spots
            grand_rev += dl.total_revenue
            grand_cancelled += row_cancelled_units

        return {
            'deal': {
                'id': self.id,
                'name': self.name or '',
                'program': self.program.display_name if self.program else '',
                'brand':   self.brands.display_name  if self.brands  else '',
                'advertiser': self.advertiser or '',
                'account': self.client_account.display_name if self.client_account else '',
                'length':  dict(self._fields['length'].selection).get(self.length, '') if self.length else '',
                'order_number': self.network_deal_number or '',
                'units_start_date': self.units_start_date.isoformat() if self.units_start_date else None,
            },
            'weeks': weeks_iso,
            'rows': rows,
            'grand_total_spots': grand_spots,
            'grand_total_revenue': grand_rev,
            'grand_total_cancelled': grand_cancelled,
            'currency': {
                'id': self.currency_id.id,
                'symbol': self.currency_id.symbol or '$',
                'position': self.currency_id.position or 'before',
            },
            # ---- Time-picker support for the editable start/end time
            # dropdowns on each row. `time_options` is the full 30-min
            # picklist from mv.schedules; `daypart_times` maps each
            # predefined daypart -> (start, end) so the front-end can
            # reverse-lookup and auto-select 'custom' when the planner
            # picks a non-matching pair.
            'time_options': [
                {'value': v, 'label': lbl}
                for v, lbl in self.env['mv.schedules']
                                 ._fields['start_time'].selection
            ],
            'daypart_times': [
                {'value': k, 'start': v[0], 'end': v[1]}
                for k, v in DAYPART_DEFAULT_TIMES.items()
            ],
        }

    # ------------------------------------------------------------------
    # Write: apply a batch of edits from the front-end
    # ------------------------------------------------------------------
    def save_units_grid(self, edits):
        """Persist a batch of edits.

        `edits` shape:
            {
              'row_updates': [{'id': 5, 'rate': 90.0, ...}, ...],
              'row_creates': [{'daypart': 'prime', 'rate': 140.0,
                               'run_start': '...', 'run_end': '...',
                               'days_mask': [t,t,t,t,t,f,f]}, ...],
              'row_deletes': [7, 9],
              'cell_updates': [{'row_id': 5, 'week': '2026-03-02',
                                'units': 20}, ...],
            }

        Returns the fresh payload from load_units_grid().
        """
        self.ensure_one()
        edits = edits or {}

        # --- Phase 12: deal-level start date update
        deal_update = edits.get('deal_update') or {}
        if 'units_start_date' in deal_update:
            self.write({'units_start_date': deal_update['units_start_date']})
            # When the deal-level start date moves, propagate the new
            # range to every existing Deal Line so the load_*_grid
            # cell-state logic no longer sees stale per-row ranges.
            new_weeks = mondays_for_start_date(self.units_start_date)
            if new_weeks:
                self.env['mv.deal_line'].search(
                    [('deal_id', '=', self.id)]
                ).write({
                    'run_start': new_weeks[0],
                    'run_end':   new_weeks[-1],
                })

        # Compute the (deal-level) week range so new Deal Lines can
        # inherit run_start / run_end from it.
        weeks = mondays_for_start_date(self.units_start_date)
        deal_run_start = weeks[0].isoformat() if weeks else None
        deal_run_end   = weeks[-1].isoformat() if weeks else None

        # --- row deletes
        if edits.get('row_deletes'):
            self.env['mv.deal_line'].browse(edits['row_deletes']).unlink()

        # --- row updates
        for upd in edits.get('row_updates') or []:
            rid = upd.pop('id', None)
            if not rid:
                continue
            days = upd.pop('days_mask', None)
            if days is not None:
                upd.update({
                    'day_mon': bool(days[0]), 'day_tue': bool(days[1]),
                    'day_wed': bool(days[2]), 'day_thu': bool(days[3]),
                    'day_fri': bool(days[4]), 'day_sat': bool(days[5]),
                    'day_sun': bool(days[6]),
                })
            dl = self.env['mv.deal_line'].browse(rid)
            dl.write(upd)
            # When the Deal Line itself changes (rate, days, start_time,
            # end_time...), propagate the new values to ALL of its
            # already-existing Schedule rows. Without this, schedules
            # created on a previous Save retain the stale rate.
            if dl.schedule_ids:
                dl.schedule_ids.write(dl.schedule_inherit_vals())

        # --- row creates
        new_ids_by_temp = {}
        for cre in edits.get('row_creates') or []:
            temp_id = cre.pop('temp_id', None)
            days = cre.pop('days_mask', None)
            vals = dict(cre, deal_id=self.id)
            # Phase 12: rows no longer carry run_start/run_end from the UI.
            # Auto-fill from the deal-level start-of-quarter range so the
            # required fields on mv.deal_line still get values.
            vals.setdefault('run_start', deal_run_start)
            vals.setdefault('run_end',   deal_run_end)
            if days is not None:
                vals.update({
                    'day_mon': bool(days[0]), 'day_tue': bool(days[1]),
                    'day_wed': bool(days[2]), 'day_thu': bool(days[3]),
                    'day_fri': bool(days[4]), 'day_sat': bool(days[5]),
                    'day_sun': bool(days[6]),
                })
            new = self.env['mv.deal_line'].create(vals)
            if temp_id is not None:
                new_ids_by_temp[temp_id] = new.id

        # --- cell updates: write units_available on the linked schedule,
        # creating one if missing. If a cell is zeroed AND a schedule
        # already exists for that (deal_line, week), DELETE the schedule
        # so the grid stays clean.
        #
        # Exception - cell_update with `cancelled: True` is a
        # cancellation marker (sent by Section 2 of the bulk allocation
        # bar): set status='canceled' on the existing schedule, KEEP
        # units_available unchanged, and DO NOT create a stub schedule
        # if none exists yet.
        Sched = self.env['mv.schedules']
        touched_dl_ids = set()
        for cu in edits.get('cell_updates') or []:
            row_id = cu.get('row_id')
            if isinstance(row_id, str) and row_id.startswith('tmp:'):
                temp = row_id[len('tmp:'):]
                row_id = new_ids_by_temp.get(temp)
            if not row_id:
                continue
            dl = self.env['mv.deal_line'].browse(row_id)
            if not dl.exists():
                # Row was deleted earlier in this same batch; skip.
                continue
            touched_dl_ids.add(dl.id)
            week_iso = cu.get('week')
            # ACTIVE schedule = anything not 'canceled'. We treat the
            # cancelled schedule(s) as historical and never touch them
            # during units writes.
            active = Sched.search([
                ('deal_line_id', '=', dl.id),
                ('week', '=', week_iso),
                ('status', '!=', 'canceled'),
            ], limit=1)

            # --- Cancellation marker (Section 2 of bulk allocation)
            if cu.get('cancelled'):
                if active:
                    # Flip the currently-active schedule to canceled.
                    # Its units_available is preserved so the front-end
                    # can render it as `x: 0/<units>` below the input.
                    active.write({'status': 'canceled'})
                # else: no active schedule -> nothing to cancel.
                continue

            # --- Standard units write (affects ONLY the active schedule)
            units = cu.get('units') or 0
            if units <= 0:
                # Zeroed cell -> drop the active schedule. Cancelled
                # schedules at the same week stay intact.
                if active:
                    active.unlink()
                continue
            # Fields the child Schedule inherits from its parent Deal Line
            # (rate, days_allowed, start_time, end_time) - centralised on
            # the Deal Line so changing them in one place propagates here.
            inherit_vals = dl.schedule_inherit_vals()
            if active:
                active.write({
                    'units_available': units,
                    **inherit_vals,
                })
            else:
                # New active schedule: default delivery to 100% so the
                # Capping Report shows it green out of the box.
                Sched.create({
                    'deal_parent': self.id,
                    'deal_line_id': dl.id,
                    'week': week_iso,
                    'units_available': units,
                    'status': 'sold',
                    'cap_pct': 100,
                    **inherit_vals,
                })

        # --- Auto-cleanup: any touched Deal Line that no longer has ANY
        # --- LTC operations queued by the front-end (Section 2 Go
        # button or the row-menu LTC dialog). Each op cancels every
        # active schedule in weeks AFTER the LTC week and splits the
        # LTC week off into a new Deal Line if days_allowed shrinks.
        # NOTE: LTC ops can reparent a schedule away from its source
        # deal_line; if that was the only schedule on the source, the
        # deal_line becomes empty. We let the broader cleanup below
        # catch this rather than tracking it inline.
        for op in edits.get('ltc_ops') or []:
            row_id = op.get('row_id')
            ltc_date = op.get('ltc_date')
            if isinstance(row_id, str) and row_id.startswith('tmp:'):
                temp = row_id[len('tmp:'):]
                row_id = new_ids_by_temp.get(temp)
            if not row_id or not ltc_date:
                continue
            self._do_apply_ltc(row_id, ltc_date)

        # --- Auto-cleanup: ANY Deal Line on this deal that no longer
        # has any linked schedule (sold OR canceled) is now empty and
        # should be deleted. Scan all of the deal's deal_lines, not
        # just touched_dl_ids, so we also catch lines that were left
        # empty by reparenting in _do_apply_ltc.
        self._unlink_empty_deal_lines()

        return self.load_units_grid()

    def _unlink_empty_deal_lines(self):
        """Delete every Deal Line on this deal that has zero linked
        schedules (whether sold or canceled). The cascade ondelete on
        schedules.deal_line_id makes this safe; we never run this when
        a schedule is mid-write."""
        self.ensure_one()
        empty = self.env['mv.deal_line'].search([
            ('deal_id', '=', self.id),
        ]).filtered(lambda d: not d.schedule_ids)
        if empty:
            empty.unlink()

    # ------------------------------------------------------------------
    # LTC ("Last To Cancel"): mid-week cancellation for one Deal Line
    # ------------------------------------------------------------------
    # Semantics:
    #   - `ltc_date` falls inside one broadcast week (the LTC week,
    #     i.e. the Monday on or before ltc_date).
    #   - Every ACTIVE schedule whose week > ltc_week_monday is
    #     cancelled (status='canceled', units preserved).
    #   - The LTC week itself stays active but its days_allowed are
    #     truncated to Mon..weekday(ltc_date) (Mon=0..Sun=6). If those
    #     truncated days differ from the parent's, the LTC-week
    #     schedule is moved to a freshly-cloned Deal Line carrying
    #     the truncated days_allowed.
    # ------------------------------------------------------------------
    def apply_ltc(self, row_id, ltc_date):
        """Public RPC entry point - applies a single LTC and returns
        the fresh grid. Used when the front-end wants an immediate
        commit. The save-on-Save flow goes through _do_apply_ltc
        directly from save_units_grid."""
        self.ensure_one()
        self._do_apply_ltc(row_id, ltc_date)
        # Same broad cleanup as save_units_grid - delete any Deal
        # Line left empty by the LTC reparenting.
        self._unlink_empty_deal_lines()
        return self.load_units_grid()

    def _do_apply_ltc(self, row_id, ltc_date):
        """Worker: cancels post-LTC-week schedules + (maybe) splits
        the LTC week into a new Deal Line. Does NOT return / refresh
        - the caller is responsible for that."""
        self.ensure_one()
        if not row_id or not ltc_date:
            return
        from datetime import date as _date, timedelta as _td
        if isinstance(ltc_date, str):
            ltc_date = _date.fromisoformat(ltc_date)

        # Stage-1 edits in save_units_grid use 'tmp:N' for unsaved
        # rows. By the time _do_apply_ltc runs, those temp ids have
        # already been resolved to real ids by save_units_grid's
        # new_ids_by_temp map - the caller is expected to pass the
        # resolved id. Defensive guard: if a 'tmp:' string slips
        # through, skip the operation rather than crashing.
        if isinstance(row_id, str) and row_id.startswith('tmp:'):
            return
        dl = self.env['mv.deal_line'].browse(row_id)
        if not dl.exists():
            return

        ltc_weekday = ltc_date.weekday()
        ltc_week_mon = ltc_date - _td(days=ltc_weekday)
        Sched = self.env['mv.schedules']

        # 1. Cancel every active schedule in weeks AFTER the LTC week.
        post_active = Sched.search([
            ('deal_line_id', '=', dl.id),
            ('week', '>', ltc_week_mon),
            ('status', '!=', 'canceled'),
        ])
        if post_active:
            post_active.write({'status': 'canceled'})

        # 2. LTC week: truncate days_allowed and (maybe) split.
        ltc_sched = Sched.search([
            ('deal_line_id', '=', dl.id),
            ('week', '=', ltc_week_mon),
            ('status', '!=', 'canceled'),
        ], limit=1)
        if ltc_sched:
            day_flags = [
                dl.day_mon, dl.day_tue, dl.day_wed,
                dl.day_thu, dl.day_fri, dl.day_sat, dl.day_sun,
            ]
            new_day_flags = [
                bool(day_flags[i]) and i <= ltc_weekday
                for i in range(7)
            ]
            if new_day_flags != day_flags:
                clone_vals = {
                    'deal_id':    dl.deal_id.id,
                    'daypart':    dl.daypart,
                    'time_range': dl.time_range or '',
                    'start_time': dl.start_time or False,
                    'end_time':   dl.end_time   or False,
                    'rate':       dl.rate,
                    'run_start':  dl.run_start,
                    'run_end':    dl.run_end,
                    'day_mon': new_day_flags[0],
                    'day_tue': new_day_flags[1],
                    'day_wed': new_day_flags[2],
                    'day_thu': new_day_flags[3],
                    'day_fri': new_day_flags[4],
                    'day_sat': new_day_flags[5],
                    'day_sun': new_day_flags[6],
                }
                new_dl = self.env['mv.deal_line'].create(clone_vals)
                ltc_sched.write({'deal_line_id': new_dl.id})
                ltc_sched.write(new_dl.schedule_inherit_vals())
        # No return - public apply_ltc / save_units_grid handle the
        # grid refresh on their own.

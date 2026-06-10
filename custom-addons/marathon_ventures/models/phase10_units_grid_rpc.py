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
        for dl in self.env['mv.deal_line'].search([('deal_id', '=', self.id)]):
            # Index schedules by week for fast lookup
            sched_by_week = {}
            for sched in dl.schedule_ids:
                if sched.week:
                    sched_by_week[sched.week.isoformat()] = sched

            cells = []
            for w_iso, w_dt in zip(weeks_iso, weeks):
                in_range = (
                    dl.run_start and dl.run_end and
                    dl.run_start <= w_dt <= dl.run_end
                )
                sched = sched_by_week.get(w_iso)
                if not in_range:
                    cells.append({
                        'week': w_iso, 'units': 0, 'state': 'hatched',
                        'sched_id': sched.id if sched else False,
                    })
                    continue
                if not sched or not sched.units_available:
                    cells.append({
                        'week': w_iso, 'units': 0, 'state': 'dashed',
                        'sched_id': sched.id if sched else False,
                    })
                    continue
                # Map cap/status -> visual state
                cap = sched.cap or 'uncapped'
                status = sched.status or ''
                state = 'green'
                if status == 'canceled':
                    state = 'gray'
                elif cap == 'ghost':
                    state = 'gray'
                elif cap in ('v_50', 'v_50_2', 'v_80', 'v_80_in_ov',
                              'v_1_2_in_pr_and_1_2_in_ov'):
                    state = 'amber'
                cells.append({
                    'week': w_iso,
                    'units': sched.units_available,
                    'state': state,
                    'sched_id': sched.id,
                })

            row = {
                'id': dl.id,
                'daypart': dl.daypart,
                'daypart_label': dict(dl._fields['daypart'].selection).get(
                    dl.daypart, dl.daypart or '',
                ),
                'time_range': dl.time_range or '',
                'days_mask': dl.days_mask(),
                'rate': dl.rate,
                'run_start': dl.run_start.isoformat() if dl.run_start else None,
                'run_end':   dl.run_end.isoformat()   if dl.run_end   else None,
                'cells': cells,
                'total_spots': dl.total_spots,
                'total_revenue': dl.total_revenue,
            }
            rows.append(row)
            grand_spots += dl.total_spots
            grand_rev += dl.total_revenue

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
            'currency': {
                'id': self.currency_id.id,
                'symbol': self.currency_id.symbol or '$',
                'position': self.currency_id.position or 'before',
            },
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
            units = cu.get('units') or 0
            sched = Sched.search([
                ('deal_line_id', '=', dl.id), ('week', '=', week_iso)
            ], limit=1)
            if units <= 0:
                # Zeroed cell -> remove the schedule entirely
                if sched:
                    sched.unlink()
                continue
            # Fields the child Schedule inherits from its parent Deal Line
            # (rate, days_allowed, start_time, end_time) - centralised on
            # the Deal Line so changing them in one place propagates here.
            inherit_vals = dl.schedule_inherit_vals()
            if sched:
                sched.write({
                    'units_available': units,
                    **inherit_vals,
                })
            else:
                # New schedule: default delivery to 100% so the Capping
                # Report shows it green out of the box. Planners can
                # cap individual cells / rows from the Capping tab.
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
        # linked schedule is now empty -> delete it. The cascade ondelete
        # on schedules.deal_line_id makes this safe (no orphan rows).
        if touched_dl_ids:
            empty_dls = self.env['mv.deal_line'].browse(list(touched_dl_ids)).filtered(
                lambda d: d.exists() and not d.schedule_ids
            )
            if empty_dls:
                empty_dls.unlink()

        return self.load_units_grid()

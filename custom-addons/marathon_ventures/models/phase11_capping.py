# -*- coding: utf-8 -*-
"""Phase 15 - Capping Report (schedules-only, no mv.deal_line).

Same signature grouping as phase10_units_grid_rpc but scoped to the
Capping tab. Uses the shared helpers from phase10 to keep the two
grids in exact sync.
"""
import logging
from odoo import models, fields, api

from odoo.addons.marathon_ventures.models.phase12_deal_start_date import (
    mondays_for_start_date,
)
from odoo.addons.marathon_ventures.models.phase10_units_grid_rpc import (
    _sig_from_schedule, _parse_sig, _days_bits_from_allowed,
    DAYPART_LABELS, _guess_daypart, _time_range_label,
    _program_daypart_payload, _guess_daypart_with_program,
    _daypart_label_with_program,
)

_logger = logging.getLogger(__name__)


class MvScheduleCapping(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    cap_pct = fields.Integer(
        string='Cap %', default=100,
        help='Percentage of booked spots that should actually deliver.',
    )
    effective_spots = fields.Float(
        string='Effective Spots',
        compute='_compute_effective_spots', store=True, digits=(17, 2),
    )

    @api.depends('units_available', 'cap_pct')
    def _compute_effective_spots(self):
        for rec in self:
            units = rec.units_available or 0.0
            pct = max(0, min(100, rec.cap_pct or 0))
            rec.effective_spots = round(units * pct / 100.0, 2)


class MvDealCappingRpc(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    _CAP_TO_PCT = {
        'uncapped': 100, 'v_80': 80, 'v_50': 50, 'v_0': 0, 'ghost': 0,
    }

    @api.model
    def _cap_pct_to_value(self, pct):
        try:
            pct = int(pct)
        except (TypeError, ValueError):
            pct = 100
        if pct >= 100: return 'uncapped'
        if pct == 80:  return 'v_80'
        if pct == 50:  return 'v_50'
        if pct == 0:   return 'v_0'
        return None

    def load_capping_grid(self):
        self.ensure_one()
        weeks = mondays_for_start_date(self.units_start_date)
        weeks_iso = [w.isoformat() for w in weeks]
        # Program-specific dayparts (same precedence as Units Grid):
        # if the program has any configured, use them for daypart
        # labels; otherwise fall back to DAYPART_LABELS.
        program_dayparts = _program_daypart_payload(self.program)

        all_scheds = self.env['mv.schedules'].search([
            ('deal_parent', '=', self.id),
        ])
        groups = {}
        for sched in all_scheds:
            sig = _sig_from_schedule(sched)
            grp = groups.setdefault(sig, {
                'active_by_week': {}, 'sample': sched,
            })
            if not sched.week or (sched.status or '') == 'canceled':
                continue
            w = sched.week.isoformat()
            prev = grp['active_by_week'].get(w)
            if prev is None or sched.id > prev.id:
                grp['active_by_week'][w] = sched

        def _row_sort_key(item):
            sig, grp = item
            samp = grp['sample']
            return (samp.start_time or '', samp.rate or 0.0)

        time_options_map = dict(
            self.env['mv.schedules']._fields['start_time'].selection or []
        )

        rows = []
        grand_booked = 0.0
        grand_effective = 0.0
        grand_revenue = 0.0
        for sig, grp in sorted(groups.items(), key=_row_sort_key):
            samp = grp['sample']
            active_by_week = grp['active_by_week']
            cells = []
            row_booked = 0.0
            row_effective = 0.0
            for w_iso in weeks_iso:
                sched = active_by_week.get(w_iso)
                if not sched or not sched.units_available:
                    cells.append({
                        'week': w_iso, 'units_booked': 0,
                        'units_effective': 0, 'cap_pct': 100,
                        'cap': 'uncapped', 'state': 'dashed',
                        'sched_id': False,
                    })
                    continue
                booked = sched.units_available
                pct = sched.cap_pct if sched.cap_pct is not None else 100
                pct = max(0, min(100, pct))
                effective = round(booked * pct / 100.0)
                if sched.status == 'canceled':
                    state = 'dashed'
                elif pct >= 100:
                    state = 'green'
                elif pct == 0:
                    state = 'gray'
                else:
                    state = 'amber'
                cells.append({
                    'week': w_iso, 'units_booked': booked,
                    'units_effective': effective, 'cap_pct': pct,
                    'cap': sched.cap or 'uncapped', 'state': state,
                    'sched_id': sched.id,
                })
                row_booked += booked
                row_effective += effective

            row_revenue = row_effective * (samp.rate or 0.0)
            daypart = _guess_daypart_with_program(
                samp.start_time, samp.end_time, program_dayparts,
            )
            days_bits = _days_bits_from_allowed(samp.days_allowed)
            rows.append({
                'id': sig, 'sig': sig,
                'daypart': daypart,
                'daypart_label': _daypart_label_with_program(
                    daypart, program_dayparts,
                ),
                'time_range': _time_range_label(
                    samp.start_time, samp.end_time, time_options_map,
                ),
                'days_mask': [b == '1' for b in days_bits],
                'rate': samp.rate,
                'run_start': weeks_iso[0] if weeks_iso else None,
                'run_end':   weeks_iso[-1] if weeks_iso else None,
                'cells': cells,
                'row_booked': row_booked,
                'row_effective': row_effective,
                'row_revenue': row_revenue,
            })
            grand_booked += row_booked
            grand_effective += row_effective
            grand_revenue += row_revenue

        return {
            'deal': {
                'id': self.id, 'name': self.name or '',
                'program': self.program.display_name if self.program else '',
                'brand':   self.brands.display_name  if self.brands  else '',
                'advertiser': self.advertiser or '',
                'account': self.client_account.display_name if self.client_account else '',
                'length':  dict(self._fields['length'].selection).get(self.length, '') if self.length else '',
                'order_number': self.network_deal_number or '',
            },
            'weeks': weeks_iso,
            'rows': rows,
            'grand_booked': grand_booked,
            'grand_effective': grand_effective,
            'grand_revenue': grand_revenue,
            'currency': {
                'symbol': self.currency_id.symbol or '$',
                'position': self.currency_id.position or 'before',
            },
            'cap_options': [
                {'value': 'uncapped', 'label': 'Uncapped', 'pct': 100},
                {'value': 'v_80',     'label': '80%',      'pct': 80},
                {'value': 'v_50',     'label': '50%',      'pct': 50},
                {'value': 'v_0',      'label': '0%',       'pct': 0},
                {'value': 'ghost',    'label': 'Ghost',    'pct': 0},
            ],
            # Program-specific dayparts. Empty list -> fall back to
            # the hardcoded labels on the frontend.
            'program_dayparts': program_dayparts,
        }

    def save_capping_grid(self, edits):
        self.ensure_one()
        edits = edits or {}
        Sched = self.env['mv.schedules']

        for cu in edits.get('cell_updates') or []:
            cap_value = cu.get('cap')
            pct = cu.get('cap_pct')
            if cap_value is not None and pct is None:
                pct = self._CAP_TO_PCT.get(cap_value, 100)
            elif cap_value is None and pct is not None:
                cap_value = self._cap_pct_to_value(pct)
            if pct is None and cap_value is None:
                continue
            if pct is not None:
                pct = max(0, min(100, int(pct)))

            sched_id = cu.get('sched_id')
            sched = Sched.browse(sched_id) if sched_id else Sched.browse([])
            if not sched_id or not sched.exists():
                sig = cu.get('row_id')
                week_iso = cu.get('week')
                if sig and week_iso and not (
                    isinstance(sig, str) and sig.startswith('tmp:')
                ):
                    matches = self._capping_schedules_for_sig(sig)
                    sched = matches.filtered(
                        lambda s: s.week and s.week.isoformat() == week_iso
                                  and (s.status or '') != 'canceled'
                    )[:1]
            if sched and sched.exists():
                vals = {}
                if pct is not None:
                    vals['cap_pct'] = pct
                if cap_value is not None:
                    vals['cap'] = cap_value
                sched.write(vals)
            else:
                _logger.warning(
                    "[MV phase11] no schedule found for cap edit: %s", cu,
                )

        for ru in edits.get('row_cap_pct') or []:
            sig = ru.get('row_id')
            pct = ru.get('cap_pct')
            # Explicit picklist choice from the frontend. When the
            # user picks "Ghost" from the Set Cap % dropdown, pct=0
            # AND cap='ghost' are both sent; without this we'd
            # reverse-map 0 -> 'v_0' and lose the ghost distinction.
            cap_explicit = ru.get('cap')
            if pct is None or not sig:
                continue
            if isinstance(sig, str) and sig.startswith('tmp:'):
                continue
            pct = max(0, min(100, int(pct)))
            # Optional date range: only apply the cap to schedules
            # whose week (Monday) falls in [start_date, end_date].
            # Blank/None on either side means "unbounded on that
            # side" so a planner can restrict just one edge.
            start_iso = (ru.get('start_date') or '').strip() or None
            end_iso   = (ru.get('end_date')   or '').strip() or None
            start_date = fields.Date.from_string(start_iso) if start_iso else None
            end_date   = fields.Date.from_string(end_iso)   if end_iso   else None
            scheds = self._capping_schedules_for_sig(sig, active_only=True)
            if start_date is not None:
                scheds = scheds.filtered(
                    lambda s: s.week and s.week >= start_date
                )
            if end_date is not None:
                scheds = scheds.filtered(
                    lambda s: s.week and s.week <= end_date
                )
            if scheds:
                vals = {'cap_pct': pct}
                # Prefer the caller-supplied cap value; only reverse-
                # map from pct as a fallback.
                cap_value = cap_explicit or self._cap_pct_to_value(pct)
                if cap_value is not None:
                    vals['cap'] = cap_value
                scheds.write(vals)

        for sig in edits.get('row_ghost_all') or []:
            if isinstance(sig, str) and sig.startswith('tmp:'):
                continue
            scheds = self._capping_schedules_for_sig(sig, active_only=True)
            if scheds:
                scheds.write({'cap_pct': 0, 'cap': 'ghost'})

        return self.load_capping_grid()

    def _capping_schedules_for_sig(self, sig, active_only=True):
        """Same as phase10._schedules_for_sig but public here for
        Capping. Uses phase10's parse_sig + days_bits helpers."""
        self.ensure_one()
        vals = _parse_sig(sig)
        domain = [
            ('deal_parent', '=', self.id),
            ('rate', '=', vals['rate']),
            ('start_time', '=', vals['start_time'] or False),
            ('end_time',   '=', vals['end_time'] or False),
            ('max_per_day', '=', vals['max_per_day']),
        ]
        if active_only:
            domain.append(('status', '!=', 'canceled'))
        candidates = self.env['mv.schedules'].search(domain)
        return candidates.filtered(
            lambda s: _days_bits_from_allowed(s.days_allowed) == vals['days_bits']
        )

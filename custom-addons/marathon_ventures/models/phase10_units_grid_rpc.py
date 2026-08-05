# -*- coding: utf-8 -*-
"""Phase 15 - Units Grid RPC (schedules-only, no mv.deal_line).

Rows are groups of mv.schedules records sharing a signature:
    days_bits | rate | start_time | end_time | max_per_day

`days_bits` is a 7-char string M-T-W-T-F-S-S computed by projecting
the schedule's days_allowed (Many2many of mv.days_allowed.tag records)
onto the fixed weekday order. Note: mv.schedules DOES NOT have
day_mon..day_sun boolean fields - those lived only on the (now-deleted)
mv.deal_line. The signature converts between the tag-based M2M and a
UI-friendly 7-bit mask.
"""
from datetime import date, timedelta
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError

from odoo.addons.marathon_ventures.models.phase12_deal_start_date import (
    mondays_for_start_date,
)


DAYPART_DEFAULT_TIMES = {
    'early_morning': ('v_06_00a', 'v_09_00a'),
    'morning':       ('v_09_00a', 'v_12_00p'),
    'day':           ('v_09_00a', 'v_06_00p'),
    'afternoon':     ('v_03_00p', 'v_06_00p'),
    'early_fringe':  ('v_06_00p', 'v_08_00p'),
    'prime':         ('v_06_00p', 'v_12_00a'),
    'late_fringe':   ('v_12_00a', 'v_03_00a'),
    'overnight':     ('v_03_00a', 'v_06_00a'),
}

DAYPART_LABELS = {
    'early_morning': 'Early Morning',
    'morning':       'Morning',
    'day':           'Daytime',
    'afternoon':     'Afternoon',
    'early_fringe':  'Early Fringe',
    'prime':         'Prime',
    'late_fringe':   'Late Fringe',
    'overnight':     'Overnight',
    'custom':        'Custom',
}

DAY_CODES = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']


# ---------------------------------------------------------------------
# Days-allowed <-> bit-string helpers
# ---------------------------------------------------------------------
def _days_bits_from_allowed(days_allowed_recordset):
    """Project a days_allowed Many2many recordset onto a 7-char M..S
    bit string. Missing == 0."""
    if not days_allowed_recordset:
        return '0' * 7
    codes = set(days_allowed_recordset.mapped('code') or [])
    return ''.join('1' if d in codes else '0' for d in DAY_CODES)


def _days_bits_from_mask(days_mask):
    """days_mask is a list of 7 truthy values [Mon,...,Sun]."""
    if not days_mask:
        return '0' * 7
    bits = ['1' if bool(v) else '0' for v in days_mask]
    return ''.join((bits + ['0'] * 7)[:7])


def _tag_ids_from_bits(env, days_bits):
    """Return mv.days_allowed.tag ids matching the '1' positions."""
    codes = [DAY_CODES[i] for i in range(7) if i < len(days_bits) and days_bits[i] == '1']
    if not codes:
        return []
    tags = env['mv.days_allowed.tag'].search([('code', 'in', codes)])
    return tags.ids


# ---------------------------------------------------------------------
# Signature helpers
# ---------------------------------------------------------------------
def _sig_from_schedule(sched):
    """Stable signature key for a schedule. Two schedules on the same
    deal with the same signature = same grid row."""
    days = _days_bits_from_allowed(sched.days_allowed)
    rate = ('%.2f' % (sched.rate or 0.0))
    start = sched.start_time or ''
    end = sched.end_time or ''
    mpd = int(sched.max_per_day or 0)
    return '%s|%s|%s|%s|%s' % (days, rate, start, end, mpd)


def _parse_sig(sig):
    """Inverse of _sig_from_schedule - returns a dict where any
    matching schedule must have these values."""
    parts = (sig or '').split('|')
    while len(parts) < 5:
        parts.append('')
    days, rate, start, end, mpd = parts[0], parts[1], parts[2], parts[3], parts[4]
    days = (days + '0' * 7)[:7]
    return {
        'days_bits': days,
        'rate': float(rate or 0.0),
        'start_time': start or False,
        'end_time': end or False,
        'max_per_day': int(mpd or 0),
    }


def _guess_daypart(start, end):
    """Reverse-lookup a hardcoded daypart from a (start, end) pair.

    Runs the same containment rules as _guess_daypart_with_program so
    the no-program-dayparts fallback stays consistent after Save:

      1. Exact interval match wins.
      2. Otherwise the smallest hardcoded daypart whose window fully
         contains the schedule wins.
      3. Nothing contains -> 'custom'.
    """
    if not start or not end:
        return 'custom'
    exact = None
    contain = []   # list of (span_minutes, key)
    for k, (dp_start, dp_end) in DAYPART_DEFAULT_TIMES.items():
        if not _daypart_contains_schedule(dp_start, dp_end, start, end):
            continue
        if dp_start == start and dp_end == end:
            exact = k
            break
        ds = _time_to_minutes(dp_start)
        de = _time_to_minutes(dp_end)
        span = _dp_span_minutes(ds, de) or 1440
        contain.append((span, k))
    if exact:
        return exact
    if contain:
        contain.sort(key=lambda t: t[0])
        return contain[0][1]
    return 'custom'


def _program_daypart_payload(program):
    """Return the program's custom dayparts serialised for the
    frontend: [{value, label, start, end, range, days_bits}].
    Empty list when the program has none configured (or program is
    falsy) so the grid falls back to DAYPART_DEFAULT_TIMES.

    `days_bits` is a 7-char string ("1111100" for M-F etc.) computed
    from the daypart's days_allowed_ids. The Units Grid uses it to
    overwrite the row's days_mask when this daypart is selected, so
    the planner doesn't have to re-tick the day checkboxes.
    """
    if not program or not getattr(program, 'daypart_ids', None):
        return []
    out = []
    for dp in program.daypart_ids:
        # Every program daypart has a days_allowed_ids many2many.
        # Reuse the existing _days_bits_from_allowed helper so the
        # bit ordering matches the schedule signature grouping.
        days_bits = '0000000'
        try:
            days_bits = _days_bits_from_allowed(dp.days_allowed_ids)
        except Exception:
            pass
        out.append({
            'value': 'prog_%d' % dp.id,   # prefix avoids clashes with
                                          # the hardcoded DAYPART keys
            'label': dp.name or '',
            'start': dp.start_time or None,
            'end':   dp.end_time   or None,
            'range': dp.time_range or '',
            'days_bits': days_bits,
        })
    return out


def _time_to_minutes(t):
    """Convert a Selection code like 'v_HH_MMa' / 'v_HH_MMp' to
    minutes since midnight (0..1439). Returns None if the code
    can't be parsed. Uses Odoo's 12A = midnight, 12P = noon
    convention.
    """
    if not t or not isinstance(t, str) or not t.startswith('v_'):
        return None
    body = t[2:]           # "HH_MMa" or "HH_MMp"
    if len(body) < 6:
        return None
    try:
        hh = int(body[0:2])
        mm = int(body[3:5])
    except ValueError:
        return None
    suf = body[5]
    if suf == 'a':
        return mm if hh == 12 else hh * 60 + mm
    if suf == 'p':
        return 12 * 60 + mm if hh == 12 else (hh + 12) * 60 + mm
    return None


def _dp_span_minutes(start_min, end_min):
    """Total minutes an interval [start, end] spans on a 24h clock.
    start == end means "24 hours" (ROS 6a-6a). end > start = simple.
    end < start = wraparound (e.g. Prime 6p-12a).
    """
    if start_min is None or end_min is None:
        return None
    if end_min == start_min:
        return 1440
    if end_min > start_min:
        return end_min - start_min
    return (1440 - start_min) + end_min


def _offset_from(start_min, at_min):
    """Minutes from `start` to `at` on a 24h clock (wraps forward)."""
    if start_min is None or at_min is None:
        return None
    if at_min >= start_min:
        return at_min - start_min
    return (1440 - start_min) + at_min


def _daypart_contains_schedule(dp_start, dp_end, sch_start, sch_end):
    """True when the schedule interval [sch_start, sch_end] fits
    fully inside the daypart interval [dp_start, dp_end]. Both are
    'v_HH_MMx' Selection codes. Handles wraparound + 24h dayparts.
    """
    ds = _time_to_minutes(dp_start)
    de = _time_to_minutes(dp_end)
    ss = _time_to_minutes(sch_start)
    se = _time_to_minutes(sch_end)
    if None in (ds, de, ss, se):
        return False
    dp_span = _dp_span_minutes(ds, de)
    sch_span = _dp_span_minutes(ss, se)
    if dp_span is None or sch_span is None:
        return False
    sch_offset = _offset_from(ds, ss)
    if sch_offset is None:
        return False
    # Schedule fits if it starts inside the daypart and ends before
    # the daypart's far edge (measured from the daypart's start).
    return sch_offset + sch_span <= dp_span


def _guess_daypart_with_program(start, end, program_dayparts):
    """Pick the best-fitting program daypart for a schedule's
    (start, end) window using containment rules:

      1. Program daypart whose interval EXACTLY matches the schedule
         wins immediately - Ex: ROS 6a-6a + Day 9a-6p, schedule 9a-6p
         -> Day (exact).
      2. Otherwise pick the daypart whose interval fully CONTAINS the
         schedule and has the smallest span (most constrained).
         Ex: ROS 6a-6a + Day 9a-6p, schedule 9a-4p -> Day (narrower
         than ROS but still contains 9a-4p).
      3. No containing daypart at all -> 'custom'. When ROS 6a-6a
         is defined for the program, every valid schedule is
         contained, so 'custom' should never happen.

    Falls back to the hardcoded _guess_daypart() when the program
    has no dayparts configured (backward compatible).
    """
    if not program_dayparts:
        return _guess_daypart(start, end)

    exact_matches = []
    contain_matches = []      # list of (span_minutes, dp_dict)
    for dp in program_dayparts:
        dp_start = dp.get('start')
        dp_end = dp.get('end')
        if not dp_start or not dp_end:
            continue
        if _daypart_contains_schedule(dp_start, dp_end, start, end):
            ds = _time_to_minutes(dp_start)
            de = _time_to_minutes(dp_end)
            dp_span = _dp_span_minutes(ds, de) or 1440
            if dp_start == start and dp_end == end:
                exact_matches.append(dp)
            else:
                contain_matches.append((dp_span, dp))

    if exact_matches:
        # If more than one exact match somehow exists, first-declared wins.
        return exact_matches[0]['value']
    if contain_matches:
        # Most constrained (smallest span) wins.
        contain_matches.sort(key=lambda m: m[0])
        return contain_matches[0][1]['value']
    return 'custom' 


def _daypart_label_with_program(daypart, program_dayparts):
    """Program dayparts win on label too. `daypart` is either a
    'prog_<id>' key or one of the DAYPART_LABELS keys."""
    if program_dayparts and daypart:
        for dp in program_dayparts:
            if dp['value'] == daypart:
                return dp['label']
    return DAYPART_LABELS.get(daypart, daypart or '')



def _translate_daypart_to_id(daypart_key):
    """Turn a frontend daypart value into a mv.program.daypart id.

    The Units Report identifies each daypart with a string key:
      * 'prog_<id>' - a program-defined daypart (id = mv.program.daypart record)
      * 'early_morning' / 'weekday' / 'weekend' / 'prime' / 'late_night' /
        'overnight' / 'ros' / 'custom' - hardcoded from DAYPART_OPTIONS

    Only the prog_ keys map to real records. Hardcoded keys aren't in
    mv.program.daypart, so we return False. Callers use the returned
    id to look up the record's `name` when resolving a schedule's
    program_daypart label.
    """
    if not daypart_key or not isinstance(daypart_key, str):
        return False
    if not daypart_key.startswith('prog_'):
        return False
    try:
        return int(daypart_key[len('prog_'):])
    except (TypeError, ValueError):
        return False

def _time_range_label(start, end, time_options_map):
    if not start and not end:
        return ''
    s = (time_options_map.get(start, start) or '').lower()
    e = (time_options_map.get(end, end) or '').lower()
    if s and e:
        return '%s - %s' % (s, e)
    return s or e


# ---------------------------------------------------------------------
# mv.deal RPC surface
# ---------------------------------------------------------------------
class MvDealUnitsGridRpc(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    def _resolve_daypart_label(self, daypart_key, start, end):
        """Return the human-readable daypart LABEL to store on a
        schedule. Precedence:
          1. `daypart_key` is 'prog_<id>' and the record exists ->
             the program daypart's `name`.
          2. Deal's program has any daypart whose interval contains
             (start, end) -> that record's `name` (containment).
          3. `daypart_key` is a hardcoded key ('day', 'prime', ...)
             -> DAYPART_LABELS[key].
          4. Guess from (start, end) via _guess_daypart -> label.
          5. Fallback -> 'Custom'.
        Called from save_units_grid create + update paths.
        """
        self.ensure_one()
        # 1. Explicit program-daypart id in the frontend payload.
        dp_id = _translate_daypart_to_id(daypart_key)
        if dp_id:
            rec = self.env['mv.program.daypart'].browse(dp_id).exists()
            if rec and rec.name:
                return rec.name
        # 2. Containment fallback against the deal's program.
        dp_id = self._find_program_daypart_for_schedule(start, end)
        if dp_id:
            rec = self.env['mv.program.daypart'].browse(dp_id).exists()
            if rec and rec.name:
                return rec.name
        # 3. Hardcoded key sent by the frontend.
        if daypart_key and daypart_key in DAYPART_LABELS:
            return DAYPART_LABELS[daypart_key]
        # 4. No key sent - infer from (start, end) via containment
        #    against DAYPART_DEFAULT_TIMES.
        if start and end:
            key = _guess_daypart(start, end)
            if key and key in DAYPART_LABELS:
                return DAYPART_LABELS[key]
        # 5. Final fallback.
        return 'Custom'

    def _find_program_daypart_for_schedule(self, start, end):
        """Return the id of the smallest program daypart on this
        deal's program whose interval contains the given (start,
        end) schedule times. Returns False when nothing matches
        or the program has no dayparts. Same precedence rules as
        _guess_daypart_with_program: exact > smallest-containing.
        """
        self.ensure_one()
        program = self.program
        if not program or not program.daypart_ids or not start or not end:
            return False
        exact = None
        contain = []
        for dp in program.daypart_ids:
            if not dp.start_time or not dp.end_time:
                continue
            if not _daypart_contains_schedule(
                dp.start_time, dp.end_time, start, end,
            ):
                continue
            if dp.start_time == start and dp.end_time == end:
                exact = dp.id
                break
            ds = _time_to_minutes(dp.start_time)
            de = _time_to_minutes(dp.end_time)
            span = _dp_span_minutes(ds, de) or 1440
            contain.append((span, dp.id))
        if exact:
            return exact
        if contain:
            contain.sort(key=lambda t: t[0])
            return contain[0][1]
        return False

    def load_units_grid(self):
        """Return the Units Grid payload."""
        self.ensure_one()
        weeks = mondays_for_start_date(self.units_start_date)
        weeks_iso = [w.isoformat() for w in weeks]
        # Fetch the program's custom dayparts once so per-row
        # classification stays cheap. Empty list -> fall back to the
        # hardcoded DAYPART_DEFAULT_TIMES.
        program_dayparts = _program_daypart_payload(self.program)

        all_scheds = self.env['mv.schedules'].search([
            ('deal_parent', '=', self.id),
        ])
        groups = {}
        for sched in all_scheds:
            sig = _sig_from_schedule(sched)
            grp = groups.setdefault(sig, {
                'active_by_week': {},
                'cancelled_by_week': {},
                'sample': sched,
            })
            if not sched.week:
                continue
            w = sched.week.isoformat()
            if (sched.status or '') == 'canceled':
                grp['cancelled_by_week'].setdefault(w, []).append(sched)
            else:
                prev = grp['active_by_week'].get(w)
                if prev is None or sched.id > prev.id:
                    if prev is not None:
                        grp['cancelled_by_week'].setdefault(w, []).append(prev)
                    grp['active_by_week'][w] = sched
                else:
                    grp['cancelled_by_week'].setdefault(w, []).append(sched)

        def _row_sort_key(item):
            sig, grp = item
            samp = grp['sample']
            return (samp.start_time or '', samp.rate or 0.0)

        time_options_map = dict(
            self.env['mv.schedules']._fields['start_time'].selection or []
        )

        rows = []
        grand_spots = 0.0
        grand_rev = 0.0
        grand_cancelled = 0.0
        for sig, grp in sorted(groups.items(), key=_row_sort_key):
            samp = grp['sample']
            active_by_week = grp['active_by_week']
            cancelled_by_week = grp['cancelled_by_week']

            cells = []
            row_active_spots = 0.0
            row_active_revenue = 0.0
            row_cancelled_units = 0.0
            for w_iso in weeks_iso:
                active = active_by_week.get(w_iso)
                cancelled_list = cancelled_by_week.get(w_iso) or []
                cancelled_units = sum(
                    (s.units_available or 0.0) for s in cancelled_list
                )
                row_cancelled_units += cancelled_units

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
                    row_active_spots += (active.units_available or 0.0)
                    row_active_revenue += (
                        (active.units_available or 0.0) * (active.rate or 0.0)
                    )

                cells.append({
                    'week': w_iso,
                    'units': active_units,
                    'state': state,
                    'sched_id': active_id,
                    'cancelled_units': cancelled_units,
                    'cancelled_sched_ids': [s.id for s in cancelled_list],
                })

            days_bits = _days_bits_from_allowed(samp.days_allowed)
            days_mask = [b == '1' for b in days_bits]
            daypart = _guess_daypart_with_program(
                samp.start_time, samp.end_time, program_dayparts,
            )
            rows.append({
                'id': sig,
                'sig': sig,
                'daypart': daypart,
                'daypart_label': _daypart_label_with_program(
                    daypart, program_dayparts,
                ),
                'time_range': _time_range_label(
                    samp.start_time, samp.end_time, time_options_map,
                ),
                'start_time': samp.start_time or False,
                'end_time':   samp.end_time   or False,
                'days_mask': days_mask,
                'rate': samp.rate or 0.0,
                'max_per_day': samp.max_per_day or 0,
                'run_start': weeks_iso[0] if weeks_iso else None,
                'run_end':   weeks_iso[-1] if weeks_iso else None,
                'cells': cells,
                'total_spots': row_active_spots,
                'total_revenue': row_active_revenue,
                'total_cancelled': row_cancelled_units,
            })
            grand_spots += row_active_spots
            grand_rev += row_active_revenue
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
            'time_options': [
                {'value': v, 'label': lbl}
                for v, lbl in self.env['mv.schedules']
                                 ._fields['start_time'].selection
            ],
            # Program-specific dayparts. Empty list when the program
            # has none configured -> frontend uses its hardcoded
            # DAYPART_OPTIONS fallback.
            'program_dayparts': program_dayparts,
            'daypart_times': [
                {'value': k, 'start': v[0], 'end': v[1]}
                for k, v in DAYPART_DEFAULT_TIMES.items()
            ],
        }

    def save_units_grid(self, edits):
        """Persist a batch of edits from the OWL Units grid."""
        self.ensure_one()
        edits = edits or {}

        deal_update = edits.get('deal_update') or {}
        if 'units_start_date' in deal_update:
            self.write({'units_start_date': deal_update['units_start_date']})

        # row_deletes: sig strings
        for sig in edits.get('row_deletes') or []:
            self._delete_row_by_sig(sig)

        # row_updates: change signature fields on all schedules of oldSig
        sig_migration = {}
        for upd in edits.get('row_updates') or []:
            old_sig = upd.get('id') or upd.get('sig')
            if not old_sig or (isinstance(old_sig, str)
                               and old_sig.startswith('tmp:')):
                continue
            new_sig = self._update_row_by_sig(old_sig, upd)
            if new_sig and new_sig != old_sig:
                sig_migration[old_sig] = new_sig

        # row_creates: capture temp_id -> signature dict for later
        # cell_update materialization
        temp_sigs = {}
        for cre in edits.get('row_creates') or []:
            temp_id = cre.get('temp_id')
            if temp_id is None:
                continue
            days = cre.get('days_mask')
            temp_sigs[str(temp_id)] = {
                'days_bits': _days_bits_from_mask(days) if days else '0' * 7,
                'rate': float(cre.get('rate') or 0.0),
                'start_time': cre.get('start_time') or False,
                'end_time': cre.get('end_time') or False,
                'max_per_day': int(cre.get('max_per_day') or 0),
                # Phase 24: carry the picked daypart into schedule creation.
                'daypart': cre.get('daypart') or '',
            }

        # cell_updates: create/update/delete schedules per (sig, week)
        Sched = self.env['mv.schedules']
        for cu in edits.get('cell_updates') or []:
            row_id = cu.get('row_id')
            week_iso = cu.get('week')
            if not row_id or not week_iso:
                continue

            if isinstance(row_id, str) and row_id.startswith('tmp:'):
                temp = row_id[len('tmp:'):]
                sig_vals = temp_sigs.get(temp)
                if not sig_vals:
                    continue
            else:
                if row_id in sig_migration:
                    row_id = sig_migration[row_id]
                sig_vals = _parse_sig(row_id)

            active = self._find_active_schedule_by_sig(sig_vals, week_iso)

            if cu.get('cancelled'):
                if active:
                    active.write({'status': 'canceled'})
                continue

            units = cu.get('units') or 0
            if units <= 0:
                if active:
                    active.unlink()
                continue

            tag_ids = _tag_ids_from_bits(self.env, sig_vals['days_bits'])
            common_vals = {
                'rate': sig_vals['rate'],
                'start_time': sig_vals['start_time'] or False,
                'end_time':   sig_vals['end_time'] or False,
                'max_per_day': sig_vals['max_per_day'],
                'days_allowed': [(6, 0, tag_ids)],
            }
            # Phase 24: store the daypart LABEL as a string on the
            # schedule. Resolves in this order:
            #   1) 'prog_<id>' -> the program daypart record's name
            #   2) program has any daypart containing (start, end)
            #      -> that record's name (containment lookup)
            #   3) hardcoded key ('day', ...) -> DAYPART_LABELS[key]
            #   4) unknown -> 'Custom'
            dp_key = sig_vals.get('daypart') if isinstance(sig_vals, dict) else None
            dp_label = self._resolve_daypart_label(
                dp_key,
                sig_vals.get('start_time'),
                sig_vals.get('end_time'),
            )
            if dp_label:
                common_vals['program_daypart'] = dp_label
            if active:
                active.write({
                    'units_available': units,
                    **common_vals,
                })
            else:
                # Default cap = 'uncapped' so the Capping Report tab
                # picks up the new schedule with the correct Selection
                # value (matches cap_pct=100 = full delivery).
                Sched.create({
                    'deal_parent': self.id,
                    'week': week_iso,
                    'units_available': units,
                    'status': 'sold',
                    'cap_pct': 100,
                    'cap': 'uncapped',
                    **common_vals,
                })

        # LTC ops
        for op in edits.get('ltc_ops') or []:
            sig = op.get('row_id') or op.get('sig')
            ltc_date = op.get('ltc_date')
            if isinstance(sig, str) and sig.startswith('tmp:'):
                continue
            if not sig or not ltc_date:
                continue
            if sig in sig_migration:
                sig = sig_migration[sig]
            self._do_apply_ltc_by_sig(sig, ltc_date)

        # Hiatus ops: for each (sig, start, end) queued by the Hiatus
        # bulk action, walk schedules matching sig whose week overlaps
        # [start, end] and strip out any weekdays whose actual
        # calendar date falls in the hiatus range. No sibling row is
        # created - the schedule simply stops running on those days.
        for op in edits.get('hiatus_ops') or []:
            sig = op.get('row_id') or op.get('sig')
            hstart = op.get('hiatus_start')
            hend = op.get('hiatus_end')
            if isinstance(sig, str) and sig.startswith('tmp:'):
                continue
            if not sig or not hstart or not hend:
                continue
            if sig in sig_migration:
                sig = sig_migration[sig]
            # Prefer the per-schedule payload the frontend now sends
            # (list of {sched_id, week, hiatus_days: [0..6]}) - it's
            # already precise. Fall back to the sig-scan path if the
            # frontend didn't pre-compute.
            payload_scheds = op.get('schedules') or []
            if payload_scheds:
                self._do_apply_hiatus_from_payload(payload_scheds)
            else:
                self._do_apply_hiatus_by_sig(sig, hstart, hend)

        # ==============================================================
        # rate_ops: bulk Update-Rate on selected rows.
        # Payload: { row_id, rate_start, rate_end, new_rate,
        #            schedules: [{sched_id, week, units}] }
        # For each affected schedule, we simply write the new rate.
        # Because rate is part of the signature, the schedule then
        # moves into a new signature group -> the grid re-renders it
        # under a new row on next load_units_grid().
        # ==============================================================
        for op in edits.get('rate_ops') or []:
            new_rate = op.get('new_rate')
            payload_scheds = op.get('schedules') or []
            if new_rate is None or not payload_scheds:
                continue
            try:
                new_rate = float(new_rate)
            except (TypeError, ValueError):
                continue
            if new_rate < 0:
                continue
            sched_ids = [
                int(s.get('sched_id'))
                for s in payload_scheds
                if s.get('sched_id')
            ]
            if not sched_ids:
                continue
            scheds = self.env['mv.schedules'].browse(sched_ids).exists()
            if scheds:
                scheds.write({'rate': new_rate})

        return self.load_units_grid()

    # ==================================================================
    # sig-based schedule lookups
    # ==================================================================
    def _find_active_schedule_by_sig(self, sig_vals, week_iso):
        """Return the ACTIVE schedule (if any) on (deal, week) matching
        the sig_vals dict. Filters by scalar fields via SQL then by
        days_bits in Python (since days_allowed is a M2M, not a
        scalar column)."""
        candidates = self.env['mv.schedules'].search([
            ('deal_parent', '=', self.id),
            ('week', '=', week_iso),
            ('status', '!=', 'canceled'),
            ('rate', '=', sig_vals['rate']),
            ('start_time', '=', sig_vals['start_time'] or False),
            ('end_time',   '=', sig_vals['end_time'] or False),
            ('max_per_day', '=', sig_vals['max_per_day']),
        ])
        for s in candidates:
            if _days_bits_from_allowed(s.days_allowed) == sig_vals['days_bits']:
                return s
        return self.env['mv.schedules']

    def _schedules_for_sig(self, sig, active_only=False):
        """Every schedule on this deal matching sig (active + cancelled
        by default)."""
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

    def _delete_row_by_sig(self, sig):
        self.ensure_one()
        self._schedules_for_sig(sig).unlink()

    def _update_row_by_sig(self, old_sig, upd):
        """Update every schedule matching old_sig with the row-level
        vals in `upd`. Return the new sig (may equal old)."""
        self.ensure_one()
        scheds = self._schedules_for_sig(old_sig)
        if not scheds:
            return old_sig
        write_vals = {}
        days = upd.get('days_mask')
        if days is not None:
            tag_ids = _tag_ids_from_bits(
                self.env, _days_bits_from_mask(days),
            )
            write_vals['days_allowed'] = [(6, 0, tag_ids)]
        for k in ('rate', 'start_time', 'end_time', 'max_per_day'):
            if k in upd:
                write_vals[k] = upd[k]
        # Phase 24: persist the daypart LABEL string on the schedules.
        # Uses the same resolver as the create path.
        if 'daypart' in upd:
            new_start = upd.get('start_time', scheds[0].start_time)
            new_end   = upd.get('end_time',   scheds[0].end_time)
            write_vals['program_daypart'] = self._resolve_daypart_label(
                upd.get('daypart'), new_start, new_end,
            )
        if not write_vals:
            return old_sig
        scheds.write(write_vals)
        return _sig_from_schedule(scheds[0])

    # ==================================================================
    # LTC (Last To Cancel)
    # ==================================================================
    def apply_ltc(self, row_id, ltc_date):
        self.ensure_one()
        if isinstance(row_id, str) and row_id.startswith('tmp:'):
            return self.load_units_grid()
        self._do_apply_ltc_by_sig(row_id, ltc_date)
        return self.load_units_grid()

    def _do_apply_ltc_by_sig(self, sig, ltc_date):
        """Cancel post-LTC-week schedules matching sig, and truncate
        the LTC-week schedule's days_allowed to Mon..weekday(ltc_date)."""
        self.ensure_one()
        if not sig or not ltc_date:
            return
        if isinstance(ltc_date, str):
            ltc_date = date.fromisoformat(ltc_date)

        ltc_weekday = ltc_date.weekday()
        ltc_week_mon = ltc_date - timedelta(days=ltc_weekday)

        matching = self._schedules_for_sig(sig, active_only=True)

        # 1. Cancel schedules after the LTC week
        post_active = matching.filtered(
            lambda s: s.week and s.week > ltc_week_mon,
        )
        if post_active:
            post_active.write({'status': 'canceled'})

        # 2. LTC week: truncate the day set on that schedule in place
        ltc_sched = matching.filtered(lambda s: s.week == ltc_week_mon)
        if ltc_sched:
            ltc_sched = ltc_sched[:1]
            vals = _parse_sig(sig)
            day_flags = [bit == '1' for bit in vals['days_bits']]
            new_flags = [
                bool(day_flags[i]) and i <= ltc_weekday
                for i in range(7)
            ]
            if new_flags != day_flags:
                new_bits = ''.join('1' if v else '0' for v in new_flags)
                tag_ids = _tag_ids_from_bits(self.env, new_bits)
                ltc_sched.write({
                    'days_allowed': [(6, 0, tag_ids)],
                })

    # Hiatus: bulk hiatus for one row (sig). Strip hiatus-covered
    # days from each matching schedule's days_allowed. No sibling
    # schedule is created - the schedule simply stops running on
    # hiatus days (its new days_bits shifts it into a fresh row
    # signature on the next load).
    # ==================================================================
    def _do_apply_hiatus_by_sig(self, sig, hstart, hend):
        self.ensure_one()
        if not sig or not hstart or not hend:
            return
        if isinstance(hstart, str):
            hstart = date.fromisoformat(hstart)
        if isinstance(hend, str):
            hend = date.fromisoformat(hend)
        if hend < hstart:
            return

        matching = self._schedules_for_sig(sig, active_only=True)
        if not matching:
            return

        for sched in matching:
            if not sched.week:
                continue
            week_mon = sched.week
            week_end = week_mon + timedelta(days=6)
            # Skip schedules whose entire week is OUTSIDE the hiatus.
            if week_end < hstart or week_mon > hend:
                continue
            cur_bits = _days_bits_from_allowed(sched.days_allowed)
            new_bits_list = list(cur_bits)
            any_removed = False
            for i in range(7):
                if cur_bits[i] != '1':
                    continue
                d = week_mon + timedelta(days=i)
                if hstart <= d <= hend:
                    new_bits_list[i] = '0'
                    any_removed = True
            if not any_removed:
                continue
            new_bits = ''.join(new_bits_list)
            if new_bits == '0' * 7:
                sched.write({'status': 'canceled'})
                continue
            new_tag_ids = _tag_ids_from_bits(self.env, new_bits)
            sched.write({'days_allowed': [(6, 0, new_tag_ids)]})

    def _do_apply_hiatus_from_payload(self, payload_scheds):
        """Apply hiatus using the exact per-schedule day list the
        frontend pre-computed. `payload_scheds` is a list of dicts:
            {'sched_id': <int>, 'week': '2026-03-02', 'hiatus_days': [0,3,6]}
        where hiatus_days is a list of weekday indices (0=Mon..6=Sun)
        to strip from that schedule's days_allowed.

        Falls back cleanly if the schedule was deleted between the
        frontend snapshot and Save."""
        self.ensure_one()
        Sched = self.env['mv.schedules']
        for entry in payload_scheds:
            sched_id = entry.get('sched_id')
            hiatus_days = entry.get('hiatus_days') or []
            if not sched_id or not hiatus_days:
                continue
            sched = Sched.browse(sched_id).exists()
            if not sched:
                continue
            cur_bits = _days_bits_from_allowed(sched.days_allowed)
            new_bits_list = list(cur_bits)
            any_removed = False
            for i in hiatus_days:
                if 0 <= i < 7 and new_bits_list[i] == '1':
                    new_bits_list[i] = '0'
                    any_removed = True
            if not any_removed:
                continue
            new_bits = ''.join(new_bits_list)
            if new_bits == '0' * 7:
                # No air days left -> cancel entirely.
                sched.write({'status': 'canceled'})
                continue
            new_tag_ids = _tag_ids_from_bits(self.env, new_bits)
            sched.write({'days_allowed': [(6, 0, new_tag_ids)]})

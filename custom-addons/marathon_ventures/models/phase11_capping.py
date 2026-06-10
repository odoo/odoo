# -*- coding: utf-8 -*-
"""Phase 11 - Capping Report.

Adds the two capping fields to mv.schedules used by the Capping Grid OWL
widget on the Deal form, then exposes load_capping_grid /
save_capping_grid RPC methods on mv.deal.

cap_pct      -> Integer 0..100, default 100. The percentage of booked
                spots that should actually deliver.
effective_spots -> computed = units_available * cap_pct / 100.
"""
from datetime import date, timedelta
from odoo import models, fields, api


def _quarter_mondays(today=None):
    today = today or date.today()
    q_start_month = ((today.month - 1) // 3) * 3 + 1
    q_start = date(today.year, q_start_month, 1)
    while q_start.weekday() != 0:
        q_start -= timedelta(days=1)
    return [q_start + timedelta(weeks=i) for i in range(13)]


# ----------------------------------------------------------------------
# mv.schedules - new fields
# ----------------------------------------------------------------------
class MvScheduleCapping(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    cap_pct = fields.Integer(
        string='Cap %',
        default=100,
        help='Percentage of booked spots that should actually deliver. '
             '100 = full delivery, 0 = ghost (booked but not delivering), '
             '50/80 = partially capped.',
    )
    effective_spots = fields.Float(
        string='Effective Spots',
        compute='_compute_effective_spots',
        store=True,
        digits=(17, 2),
    )

    @api.depends('units_available', 'cap_pct')
    def _compute_effective_spots(self):
        for rec in self:
            units = rec.units_available or 0.0
            pct = max(0, min(100, rec.cap_pct or 0))
            rec.effective_spots = round(units * pct / 100.0, 2)


# ----------------------------------------------------------------------
# mv.deal - RPC methods
# ----------------------------------------------------------------------
class MvDealCappingRpc(models.Model):
    _name = 'mv.deal'
    _inherit = 'mv.deal'

    def load_capping_grid(self):
        """Return the data the Capping Grid OWL widget needs."""
        self.ensure_one()
        # Phase 12: derive week columns from the deal-level start date
        from odoo.addons.marathon_ventures.models.phase12_deal_start_date \
            import mondays_for_start_date
        weeks = mondays_for_start_date(self.units_start_date)
        weeks_iso = [w.isoformat() for w in weeks]

        rows = []
        grand_booked = 0.0
        grand_effective = 0.0
        grand_revenue = 0.0
        for dl in self.env['mv.deal_line'].search([('deal_id', '=', self.id)]):
            sched_by_week = {
                s.week.isoformat(): s for s in dl.schedule_ids if s.week
            }
            cells = []
            row_booked = 0.0
            row_effective = 0.0
            for w_iso, w_dt in zip(weeks_iso, weeks):
                # Phase 12: week columns are already filtered to the
                # deal's quarter, so every visible week is in-range.
                sched = sched_by_week.get(w_iso)
                if not sched or not sched.units_available:
                    cells.append({
                        'week': w_iso, 'units_booked': 0,
                        'units_effective': 0, 'cap_pct': 100,
                        'state': 'dashed', 'sched_id': False,
                    })
                    continue
                booked = sched.units_available
                pct = sched.cap_pct if sched.cap_pct is not None else 100
                # clamp
                pct = max(0, min(100, pct))
                effective = round(booked * pct / 100.0, 2)
                if pct >= 100:
                    state = 'green'
                elif pct == 0:
                    state = 'gray'
                else:
                    state = 'amber'
                cells.append({
                    'week': w_iso,
                    'units_booked': booked,
                    'units_effective': effective,
                    'cap_pct': pct,
                    'state': state,
                    'sched_id': sched.id,
                })
                row_booked += booked
                row_effective += effective

            row_revenue = row_effective * (dl.rate or 0.0)
            rows.append({
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
        }

    def save_capping_grid(self, edits):
        """Apply cap_pct edits to schedules.

        edits = {
          'cell_updates':  [{row_id, week, cap_pct}, ...],
          'row_cap_pct':   [{row_id, cap_pct}, ...]   # mass-set whole row
          'row_ghost_all': [row_id, ...]              # set cap_pct=0 for the row's in-range schedules
        }
        """
        self.ensure_one()
        edits = edits or {}
        Sched = self.env['mv.schedules']

        # --- Individual cell cap_pct updates
        # Prefer sched_id (sent from the front-end payload) for a direct
        # browse/write. Fall back to (deal_line_id, week) search if the
        # front-end didn't have a sched_id for some reason.
        import logging
        _logger = logging.getLogger(__name__)
        for cu in edits.get('cell_updates') or []:
            pct = cu.get('cap_pct')
            if pct is None:
                continue
            pct = max(0, min(100, int(pct)))
            sched_id = cu.get('sched_id')
            sched = Sched.browse(sched_id) if sched_id else Sched.browse([])
            if not sched_id or not sched.exists():
                row_id = cu.get('row_id')
                week_iso = cu.get('week')
                if row_id and week_iso:
                    sched = Sched.search([
                        ('deal_line_id', '=', row_id),
                        ('week', '=', week_iso),
                    ], limit=1)
            if sched and sched.exists():
                sched.write({'cap_pct': pct})
                _logger.info(
                    "[MV phase11] cap_pct write OK: sched=%s pct=%s",
                    sched.id, pct,
                )
            else:
                _logger.warning(
                    "[MV phase11] no schedule found for cap edit: %s", cu,
                )

        # --- Mass-set the whole row to one cap %
        for ru in edits.get('row_cap_pct') or []:
            row_id = ru.get('row_id')
            pct = ru.get('cap_pct')
            if pct is None or not row_id:
                continue
            pct = max(0, min(100, int(pct)))
            dl = self.env['mv.deal_line'].browse(row_id)
            if dl.exists() and dl.schedule_ids:
                dl.schedule_ids.write({'cap_pct': pct})

        # --- Ghost-all a row (cap_pct=0)
        for row_id in edits.get('row_ghost_all') or []:
            dl = self.env['mv.deal_line'].browse(row_id)
            if dl.exists() and dl.schedule_ids:
                dl.schedule_ids.write({'cap_pct': 0})

        return self.load_capping_grid()

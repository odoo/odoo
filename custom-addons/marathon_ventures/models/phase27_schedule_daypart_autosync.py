# -*- coding: utf-8 -*-
"""Phase 27 - Auto-sync program_daypart when Schedule times change.

Requirement:
  When a Schedule record is edited and its Start Time or End Time is
  modified, the Program Daypart field should be recalculated and
  updated automatically. The calculation should use the same
  containment logic that is currently implemented for the Units
  Report save flow (`mv.deal._resolve_daypart_label`).

The Units Report save flow already writes `program_daypart`, so this
hook is only strictly needed for the OTHER paths that mutate schedule
times - the Schedule form's Start Time / End Time widgets, mass
updates, external RPC callers, and the backfill migration.

Recursion note:
  The inner write we issue only touches `program_daypart`, never
  start_time / end_time, so the outer `times_changed` branch does
  not re-enter. We also call `super().write(...)` on the inner
  update to bypass our own override entirely.
"""
import logging

from odoo import models, api

_logger = logging.getLogger(__name__)


class MvSchedulesAutoDaypart(models.Model):
    _name = 'mv.schedules'
    _inherit = 'mv.schedules'

    # ------------------------------------------------------------------
    # Create: fill program_daypart when the caller did not set it.
    # ------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            if rec.program_daypart:
                continue          # caller (e.g. Units Grid save) set it
            self._mv_backfill_program_daypart_on(rec)
        return records

    # ------------------------------------------------------------------
    # Write: whenever times change and the caller is not explicitly
    # setting program_daypart, recompute and store it.
    # ------------------------------------------------------------------
    def write(self, vals):
        times_changed = ('start_time' in vals) or ('end_time' in vals)
        manual_daypart = ('program_daypart' in vals)
        result = super().write(vals)
        if times_changed and not manual_daypart:
            for rec in self:
                self._mv_backfill_program_daypart_on(rec)
        return result

    # ------------------------------------------------------------------
    # Helper: compute and store program_daypart for one record.
    #
    # Delegates label resolution to mv.deal._resolve_daypart_label so
    # the containment logic + hardcoded fallback stays in exactly one
    # place. Passes daypart_key=None so the resolver walks:
    #   containment against deal.program.daypart_ids
    #   -> hardcoded key by _guess_daypart(start, end)
    #   -> 'Custom' final fallback.
    # ------------------------------------------------------------------
    def _mv_backfill_program_daypart_on(self, rec):
        if not rec.start_time or not rec.end_time:
            return
        deal = rec.deal_parent
        if not deal:
            return
        try:
            label = deal._resolve_daypart_label(
                None, rec.start_time, rec.end_time,
            )
        except Exception:
            _logger.exception(
                "Auto-daypart resolve failed for schedule id=%s "
                "(deal_id=%s, start=%s, end=%s)",
                rec.id, deal.id, rec.start_time, rec.end_time,
            )
            return
        if not label:
            return
        if (rec.program_daypart or '') == label:
            return
        # super() write bypasses our own override -> no recursion.
        super(MvSchedulesAutoDaypart, rec).write({
            'program_daypart': label,
        })

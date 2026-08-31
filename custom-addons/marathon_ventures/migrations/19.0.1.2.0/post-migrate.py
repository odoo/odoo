# -*- coding: utf-8 -*-
"""Phase 27 - One-time backfill of mv.schedules.program_daypart.

Runs during the module upgrade to 19.0.1.2.0. For every schedule
whose `program_daypart` is empty AND that has both start_time and
end_time set, we resolve the label using the same containment
logic the Units Report save flow uses
(mv.deal._resolve_daypart_label) and store it on the record.

Idempotent: skips rows that already have a value, so running the
upgrade twice is safe. Batches the recordset in chunks of 500 so a
very large dataset doesn't OOM the ORM cache.
"""
import logging

_logger = logging.getLogger(__name__)


def _iter_batches(records, size=500):
    total = len(records)
    for start in range(0, total, size):
        yield records[start:start + size]


def migrate(cr, version):
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    Schedule = env['mv.schedules']

    # Legacy labels that were retired when the hardcoded bucket list
    # was trimmed to match the frontend (DAYPART_OPTIONS). Rows still
    # carrying any of these get re-resolved via containment so the
    # stored label matches what the report now displays.
    legacy_labels = ['Daytime', 'Morning', 'Afternoon', 'Early Fringe']

    targets = Schedule.search([
        '|', '|',
            ('program_daypart', '=', False),
            ('program_daypart', '=', ''),
            ('program_daypart', 'in', legacy_labels),
        ('start_time', '!=', False),
        ('end_time', '!=', False),
    ])
    total = len(targets)
    if not total:
        _logger.info(
            "Phase 27 backfill: 0 schedules to update (all rows already "
            "have program_daypart set).",
        )
        return

    _logger.info(
        "Phase 27 backfill: %d schedule(s) missing program_daypart. "
        "Resolving labels via containment logic in batches of 500.",
        total,
    )

    updated = 0
    skipped_no_deal = 0
    skipped_no_label = 0
    for batch in _iter_batches(targets):
        for rec in batch:
            deal = rec.deal_parent
            if not deal:
                skipped_no_deal += 1
                continue
            try:
                label = deal._resolve_daypart_label(
                    None, rec.start_time, rec.end_time,
                )
            except Exception:
                _logger.exception(
                    "Phase 27 backfill: resolve failed for schedule id=%s "
                    "deal_id=%s (start=%s, end=%s)",
                    rec.id, deal.id, rec.start_time, rec.end_time,
                )
                continue
            if not label:
                skipped_no_label += 1
                continue
            # Direct SQL update bypasses ALL create/write overrides
            # so we don't accidentally recurse into the phase27 hook
            # while the migration is walking the same recordset.
            cr.execute(
                "UPDATE mv_schedules SET program_daypart = %s WHERE id = %s",
                (label, rec.id),
            )
            updated += 1
        # Flush the ORM cache between batches so we don't hoard memory.
        env.invalidate_all()

    _logger.info(
        "Phase 27 backfill complete. updated=%d, skipped_no_deal=%d, "
        "skipped_no_label=%d, total_considered=%d",
        updated, skipped_no_deal, skipped_no_label, total,
    )

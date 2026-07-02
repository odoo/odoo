# -*- coding: utf-8 -*-
"""Post-init / post-update hooks for the marathon_ventures module.

Runs after the module's data files have been loaded, giving us a
window to backfill data on newly-added fields."""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Ensure every mv.report has a report_type_id.

    Migration story (Phase 14 v3 -> v4):
      - v3 stored model_id directly on mv.report.
      - v4 makes model_id a related field derived from
        report_type_id.base_model_id.
      - Legacy rows have model_id set but no report_type_id. Left
        alone, they would appear "modelless" in the UI and any write
        would recompute model_id -> None (data loss).
      - Fix: for each such row, fetch-or-create a base-only Report
        Type for its former model_id, and point report_type_id at it.

    Also idempotent: on module upgrade after the initial migration,
    nothing to do (no legacy rows without report_type_id remain).
    """
    Report = env['mv.report'].sudo()
    ReportType = env['mv.report.type'].sudo()

    # Rows that predate v4 - identify them by having a model_id set
    # while report_type_id is still NULL.
    legacy = Report.search([
        ('report_type_id', '=', False),
        ('model_id', '!=', False),
    ])
    if not legacy:
        _logger.info('mv.report v4 migration: nothing to backfill')
        return

    _logger.info('mv.report v4 migration: backfilling %d legacy row(s)',
                 len(legacy))
    # Group by model_id so we create at most one default Report Type
    # per model. `related` sync will populate model_id from
    # report_type_id.base_model_id on the next write.
    by_model = {}
    for r in legacy:
        by_model.setdefault(r.model_id.id, env[Report._name].browse())
        by_model[r.model_id.id] |= r

    for model_id, rows in by_model.items():
        rt = ReportType.get_or_create_default(model_id)
        rows.write({'report_type_id': rt.id})
        _logger.info(
            '  model_id=%s -> Report Type "%s" (id=%s), %d row(s) updated',
            model_id, rt.name, rt.id, len(rows),
        )

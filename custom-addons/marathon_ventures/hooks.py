# -*- coding: utf-8 -*-
"""Post-init / post-update hooks for the marathon_ventures module."""
import logging

_logger = logging.getLogger(__name__)


def post_init_hook(env):
    """Runs after the module's data files have been loaded.

    Two migrations live here:
      1. Phase 14 v4: backfill report_type_id on legacy mv.report rows
         (v3 -> v4 report-model shift).
      2. Phase 15: nothing to do at post-init time because the actual
         mv.deal_line table drop happens in the pre-migration script
         (migrations/19.0.1.1.0/pre-migration.py). Any post-init
         cleanup would run AFTER Odoo has already tried to load the
         registry against the old schema, which is too late.
    """
    _migrate_reports_to_report_types(env)


def _migrate_reports_to_report_types(env):
    """Ensure every mv.report has a report_type_id.

    Legacy rows have model_id set but no report_type_id. Fetch (or
    auto-create) a base-only Report Type for the model, then point
    the report at it. Idempotent."""
    Report = env['mv.report'].sudo()
    ReportType = env['mv.report.type'].sudo()

    legacy = Report.search([
        ('report_type_id', '=', False),
        ('model_id', '!=', False),
    ])
    if not legacy:
        _logger.info('mv.report v4 migration: nothing to backfill')
        return

    _logger.info(
        'mv.report v4 migration: backfilling %d legacy row(s)', len(legacy),
    )
    by_model = {}
    for r in legacy:
        by_model.setdefault(r.model_id.id, Report.browse())
        by_model[r.model_id.id] |= r

    for model_id, rows in by_model.items():
        rt = ReportType.get_or_create_default(model_id)
        rows.write({'report_type_id': rt.id})
        _logger.info(
            '  model_id=%s -> Report Type "%s" (id=%s), %d row(s)',
            model_id, rt.name, rt.id, len(rows),
        )

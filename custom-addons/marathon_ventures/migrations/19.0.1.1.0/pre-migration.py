# -*- coding: utf-8 -*-
"""Phase 15 pre-migration: purge mv.deal_line and its FK on mv.schedules.

Runs BEFORE Odoo re-syncs the schema for module 'marathon_ventures'
version 19.0.1.1.0.

Why manual SQL:
  - The model class has been removed from the module. On upgrade
    Odoo won't drop the DB table on its own; leaving the FK on
    mv_schedules.deal_line_id would fail on the first attempt to
    delete a Deal Line row via cascade.
  - Schedules keep their own copies of day flags / rate / times /
    max_per_day (populated by legacy schedule_inherit_vals), so
    dropping the deal_line rows loses no schedule data.

This script is idempotent: re-runs on a DB that's already been
purged are a no-op.
"""
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        # Fresh install (no previous version): nothing to migrate.
        return

    # Break the FK first so dropping deal_lines doesn't cascade to
    # schedules. Also drop the column entirely since the model no
    # longer declares it.
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'mv_schedules' AND column_name = 'deal_line_id'
    """)
    if cr.fetchone():
        _logger.info('Phase 15 migration: dropping mv_schedules.deal_line_id')
        cr.execute(
            "ALTER TABLE mv_schedules DROP COLUMN deal_line_id CASCADE"
        )

    # Drop the mv_deal_line table entirely.
    cr.execute("""
        SELECT table_name FROM information_schema.tables
        WHERE table_name = 'mv_deal_line'
    """)
    if cr.fetchone():
        _logger.info('Phase 15 migration: dropping mv_deal_line table')
        cr.execute("DROP TABLE mv_deal_line CASCADE")

    # Clean up ir.model / ir.model.fields records that used to point
    # at mv.deal_line so the registry doesn't complain on load.
    cr.execute("DELETE FROM ir_model_fields WHERE model = 'mv.deal_line'")
    cr.execute("DELETE FROM ir_model_data "
               "WHERE model = 'ir.model.fields' "
               "  AND res_id IN ("
               "    SELECT id FROM ir_model_fields WHERE model = 'mv.deal_line'"
               "  )")
    cr.execute("DELETE FROM ir_model WHERE model = 'mv.deal_line'")
    cr.execute("DELETE FROM ir_model_data "
               "WHERE model = 'ir.model' "
               "  AND name = 'model_mv_deal_line'")

    # And any inherited-model records that referenced the deal_line
    # relation on mv.schedules.
    cr.execute("""
        DELETE FROM ir_model_data
        WHERE module = 'marathon_ventures'
          AND name IN ('access_mv_deal_line_user',
                       'model_mv_deal_line',
                       'field_mv_schedules__deal_line_id')
    """)

    # Nuke cached ir.ui.view records that still reference deal_line_id
    # in their DB-stored arch. Odoo loads data files in manifest order
    # and validates the base view against ALL inherits AT UPSERT TIME.
    # If the DB still holds an old phase9 arch adding deal_line_id,
    # the base-view upsert crashes ("field doesn't exist" - we already
    # removed the field from the model). Deleting the stale records
    # here forces Odoo to recreate them fresh from the current XML.
    # Only delete INHERIT views. Deleting the base view would violate
    # the RESTRICT FK constraint on ir_ui_view.inherit_id from every
    # child that points at it. The base view's stored arch is already
    # clean (no deal_line_id); the problem was the phase9 INHERIT
    # arch cached in the DB - deleting it forces Odoo to re-create it
    # from the current (clean) XML file later in the same load pass.
    for xmlid in ('view_mv_schedules_form_phase9_layout',
                  'view_mv_schedules_form_phase1'):
        cr.execute("""
            DELETE FROM ir_ui_view
             WHERE id IN (
                SELECT res_id FROM ir_model_data
                 WHERE module = 'marathon_ventures'
                   AND name = %s
                   AND model = 'ir.ui.view'
             )
        """, (xmlid,))
        cr.execute("""
            DELETE FROM ir_model_data
             WHERE module = 'marathon_ventures'
               AND name = %s
               AND model = 'ir.ui.view'
        """, (xmlid,))
    _logger.info('Phase 15 migration: complete')

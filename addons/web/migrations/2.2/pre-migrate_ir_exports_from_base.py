"""Pre-migration: ``ir.exports`` and ``ir.exports.line`` moved from ``base`` into ``web``.

The records stay -- the two tables and the two access rows -- only their owner
changes. Every ``ir_model_data`` row ``base`` wrote for the models is re-homed
to ``web`` so that ``web``'s reflection and data load find and update the same
records instead of creating new ones, and so that ``_process_end`` does not
reap ``base``'s rows as orphans and the records behind them with it.

A row is left alone when ``web`` already owns one of the same name: the
reflection of a shared model gives every module its own ``model_ir_exports``
and ``field_ir_exports__id``, so ``base``'s copy is then just a duplicate and
``_process_end`` drops the stale xml id while keeping the record.

The export presets consumers ship (``project``, ``hr_timesheet``,
``sale_project``, ``sale_timesheet`` and the enterprise ones) are theirs and
never change hands.
"""

import logging

_logger = logging.getLogger(__name__)

XMLID_PATTERNS = (
    "model_ir_exports",
    "model_ir_exports_line",
    "field_ir_exports__%",
    "field_ir_exports_line__%",
    "constraint_ir_exports_%",
    "access_ir_exports_group_system",
    "access_ir_exports_line_group_system",
)


def migrate(cr, version):
    if not version:
        return
    moved = 0
    for pattern in XMLID_PATTERNS:
        cr.execute(
            """
                UPDATE ir_model_data d SET module = 'web'
                 WHERE d.module = 'base'
                   AND d.name LIKE %s
                   AND NOT EXISTS (
                       SELECT 1 FROM ir_model_data e
                        WHERE e.module = 'web' AND e.name = d.name
                   )
            """,
            (pattern,),
        )
        moved += cr.rowcount
    _logger.info("web 2.2: %d ir.exports xml id(s) re-homed from base", moved)

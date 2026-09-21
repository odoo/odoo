import logging

from odoo.db import schema

_logger = logging.getLogger(__name__)

# `auto_post` answered three questions in one column: whether the entry posts
# itself, whether it repeats, and how often. The cadence half is
# `mixin.recurrence.rule`'s now, so `monthly`, `quarterly` and `yearly` become
# the mode `recurring` plus the interval the old `deltas` table decoded them to.
_CADENCE = {
    "monthly": (1, "month"),
    "quarterly": (3, "month"),
    "yearly": (1, "year"),
}


def migrate(cr, version):
    if not version:
        return

    # `repeat_until` carries the dates `auto_post_until` held. Renaming rather
    # than adding keeps the column's NOT NULL and default naming consistent
    # with a fresh install (base 1.41), and keeps the values without a copy.
    if schema.column_exists(cr, "account_move", "auto_post_until"):
        schema.rename_column(cr, "account_move", "auto_post_until", "repeat_until")

    for column, sql_type in (
        ("repeat_interval", "int4"),
        ("repeat_unit", "varchar"),
        ("repeat_type", "varchar"),
    ):
        if not schema.column_exists(cr, "account_move", column):
            schema.create_column(cr, "account_move", column, sql_type)

    # Defaults for every existing row, so the columns match what a fresh
    # install writes before the cadence mapping below narrows them.
    cr.execute("""
        UPDATE account_move
           SET repeat_interval = COALESCE(repeat_interval, 1),
               repeat_unit = COALESCE(repeat_unit, 'month')
         WHERE repeat_interval IS NULL
            OR repeat_unit IS NULL
    """)

    for old_value, (interval, unit) in _CADENCE.items():
        cr.execute(
            """
            UPDATE account_move
               SET auto_post = 'recurring',
                   repeat_interval = %s,
                   repeat_unit = %s
             WHERE auto_post = %s
            """,
            (interval, unit, old_value),
        )
        if cr.rowcount:
            _logger.info(
                "account 1.19: %d move(s) with auto_post=%s now recur every %s %s.",
                cr.rowcount,
                old_value,
                interval,
                unit,
            )

    # An end date is what used to mean "this series stops"; an empty one meant
    # forever. `repeat_type` says which now, and `repeat_until` is computed to
    # clear itself when it is not 'until', so the two cannot disagree.
    cr.execute("""
        UPDATE account_move
           SET repeat_type = CASE
                   WHEN auto_post = 'recurring' AND repeat_until IS NOT NULL
                   THEN 'until'
                   ELSE 'forever'
               END
         WHERE repeat_type IS NULL
            OR (auto_post = 'recurring' AND repeat_until IS NOT NULL
                AND repeat_type != 'until')
    """)

    # A saved filter or a stored domain naming the retired values matches
    # nothing in silence, so name them rather than rewrite them blind.
    cr.execute("""
        SELECT id, name
          FROM ir_filters
         WHERE domain LIKE '%auto_post%'
           AND (domain LIKE '%monthly%' OR domain LIKE '%quarterly%'
                OR domain LIKE '%yearly%' OR domain LIKE '%auto_post_until%')
    """)
    for filter_id, name in cr.fetchall():
        _logger.warning(
            "account 1.19: ir.filters %d (%s) still names a retired auto_post"
            " value or auto_post_until; it will match nothing until corrected.",
            filter_id,
            name,
        )

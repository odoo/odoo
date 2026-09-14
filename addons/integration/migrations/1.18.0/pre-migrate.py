import logging

from odoo.tools import SQL

_logger = logging.getLogger(__name__)

_PERIOD_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
}


def _tables_carrying_both_spellings(cr):
    cr.execute(
        """
        SELECT table_name
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND column_name IN ('rate_limit_period', 'rate_limit_window_seconds')
         GROUP BY table_name
        HAVING count(DISTINCT column_name) = 2
        """
    )
    return [row[0] for row in cr.fetchall()]


def _drop_the_column_here(cr, table):
    cr.execute(
        """
        DELETE FROM ir_model_fields f
              USING ir_model m
              WHERE f.model_id = m.id
                AND f.name = 'rate_limit_period'
                AND replace(m.model, '.', '_') = %s
        """,
        (table,),
    )
    dropped_definitions = cr.rowcount
    cr.execute(
        SQL(
            "ALTER TABLE %s DROP COLUMN IF EXISTS rate_limit_period",
            SQL.identifier(table),
        )
    )
    _logger.info(
        "%s: dropped rate_limit_period (%s field definition(s) removed)",
        table,
        dropped_definitions,
    )


def migrate(cr, version):
    if not version:
        return

    for table in _tables_carrying_both_spellings(cr):
        for period, seconds in _PERIOD_SECONDS.items():
            cr.execute(
                SQL(
                    """
                    UPDATE %s
                       SET rate_limit_window_seconds = %s
                     WHERE rate_limit_period = %s
                       AND (rate_limit_window_seconds IS NULL
                            OR rate_limit_window_seconds <= 0)
                    """,
                    SQL.identifier(table),
                    seconds,
                    period,
                )
            )
            if cr.rowcount:
                _logger.info(
                    "%s: carried %s row(s) from rate_limit_period=%r to "
                    "rate_limit_window_seconds=%s",
                    table,
                    cr.rowcount,
                    period,
                    seconds,
                )
        _drop_the_column_here(cr, table)

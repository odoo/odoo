import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """`time_type` was a Selection in two modules; it is a kernel record now.

    The schedule exception's kind moves from a two-value Selection to a link at
    `resource.time.type`, whose records this version ships. `leave` is the absence
    the schedule subtracts, and `other` -- which the exception labelled "Other" and
    the leave type labelled "Worked Time", the same value under inverted labels --
    is time that stays in the schedule.

    Runs post-migrate because the kernel records are module data, loaded before it --
    and it maps **every** row, not the ones whose kind is still NULL. The ORM fills a
    new required field with its default while it adds the column, which is before this
    runs, so by now every row already says "absence" whether it was one or not. A
    migration that skipped the non-NULL rows would read 0 and leave every `other` row
    silently converted.
    """
    cr.execute("""
        SELECT res_id, module || '.' || name
          FROM ir_model_data
         WHERE module = 'resource'
           AND name IN ('time_type_work', 'time_type_leave')
    """)
    by_xmlid = {name: res_id for res_id, name in cr.fetchall()}
    leave = by_xmlid.get("resource.time_type_leave")
    work = by_xmlid.get("resource.time_type_work")
    if not (leave and work):
        _logger.error(
            "resource 1.18: the kernel kinds of time are missing, so no exception "
            "could be given one; every schedule exception still has a NULL kind."
        )
        return

    cr.execute("""
        SELECT 1 FROM information_schema.columns
         WHERE table_name = 'resource_schedule_exception' AND column_name = 'time_type'
    """)
    if not cr.fetchone():
        _logger.info("resource 1.18: no time_type column to read; nothing to map.")
        return

    cr.execute(
        """
        UPDATE resource_schedule_exception
           SET time_type_id = CASE WHEN time_type = 'other' THEN %s ELSE %s END
    """,
        (work, leave),
    )
    _logger.info("resource 1.18: %d schedule exception(s) given a kind.", cr.rowcount)
    cr.execute(
        "ALTER TABLE resource_schedule_exception DROP COLUMN IF EXISTS time_type"
    )

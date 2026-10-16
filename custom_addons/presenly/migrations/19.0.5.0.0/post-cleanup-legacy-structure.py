import logging


_logger = logging.getLogger(__name__)


LEGACY_REFERENCE_COLUMNS = (
    ('hr_attendance', 'presenly_unit_id'),
    ('hr_leave', 'presenly_unit_id'),
    ('presenly_approval_rule', 'unit_id'),
    ('presenly_attendance_event', 'unit_id'),
    ('presenly_permission', 'unit_id'),
)

LEGACY_RELATION_TABLES = (
    'hr_department_presenly_unit_rel',
    'presenly_unit_res_users_rel',
)


def _table_exists(cr, table):
    cr.execute('SELECT to_regclass(%s)', (f'public.{table}',))
    return bool(cr.fetchone()[0])


def _column_exists(cr, table, column):
    cr.execute(
        """
        SELECT 1
          FROM information_schema.columns
         WHERE table_schema = 'public'
           AND table_name = %s
           AND column_name = %s
        """,
        (table, column),
    )
    return bool(cr.fetchone())


def _count(cr, table, where='TRUE'):
    cr.execute(f'SELECT COUNT(*) FROM "{table}" WHERE {where}')
    return cr.fetchone()[0]


def migrate(cr, version):
    """Remove retired Unit/Location schema only when it is provably unused.

    Databases with legacy Work Location rows or populated legacy foreign keys
    are preserved for manual migration. The script is idempotent and can be
    safely re-run by a later module upgrade.
    """
    if not _table_exists(cr, 'presenly_unit'):
        return

    blockers = []
    if _table_exists(cr, 'presenly_work_location'):
        location_count = _count(cr, 'presenly_work_location')
        if location_count:
            blockers.append(
                f'presenly_work_location contains {location_count} row(s)'
            )

    for table, column in LEGACY_REFERENCE_COLUMNS:
        if _table_exists(cr, table) and _column_exists(cr, table, column):
            reference_count = _count(cr, table, f'"{column}" IS NOT NULL')
            if reference_count:
                blockers.append(
                    f'{table}.{column} contains {reference_count} reference(s)'
                )

    # Unknown incoming foreign keys indicate another addon still depends on
    # the retired schema. Known Presenly FKs are removed below in a fixed order.
    known_referencing_tables = {
        table for table, _column in LEGACY_REFERENCE_COLUMNS
    } | set(LEGACY_RELATION_TABLES) | {
        'presenly_unit',
        'presenly_unit_res_users_rel',
        'presenly_work_location',
    }
    cr.execute(
        """
        SELECT DISTINCT conrelid::regclass::text
          FROM pg_constraint
         WHERE contype = 'f'
           AND confrelid IN (
               to_regclass('public.presenly_unit'),
               to_regclass('public.presenly_work_location')
           )
        """
    )
    unknown_references = sorted(
        table for (table,) in cr.fetchall()
        if table not in known_referencing_tables
    )
    if unknown_references:
        blockers.append(
            'unknown foreign keys from: %s' % ', '.join(unknown_references)
        )

    if blockers:
        _logger.warning(
            'Legacy Presenly Unit/Location schema was preserved: %s.',
            '; '.join(blockers),
        )
        return

    for table, column in LEGACY_REFERENCE_COLUMNS:
        if _table_exists(cr, table) and _column_exists(cr, table, column):
            cr.execute(f'ALTER TABLE "{table}" DROP COLUMN "{column}"')

    for table in LEGACY_RELATION_TABLES:
        cr.execute(f'DROP TABLE IF EXISTS "{table}"')

    cr.execute('DROP TABLE IF EXISTS presenly_work_location')
    cr.execute('DROP TABLE IF EXISTS presenly_unit')
    _logger.info(
        'Removed unused legacy Presenly Unit/Location columns and tables.'
    )

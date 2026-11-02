import logging


_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Drop the retired assignment table only when it is provably empty."""
    cr.execute("SELECT to_regclass('public.presenly_employee_assignment')")
    if not cr.fetchone()[0]:
        return

    cr.execute('SELECT COUNT(*) FROM presenly_employee_assignment')
    row_count = cr.fetchone()[0]
    if row_count:
        _logger.warning(
            'Retired table presenly_employee_assignment contains %s row(s); '
            'it was preserved for manual review.',
            row_count,
        )
        return

    cr.execute('DROP TABLE presenly_employee_assignment')
    _logger.info('Dropped empty retired table presenly_employee_assignment.')

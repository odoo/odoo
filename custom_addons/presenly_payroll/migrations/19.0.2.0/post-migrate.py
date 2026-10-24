import logging
from datetime import date

import calendar

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """Backfill ``work_location_id`` on existing payslips.

    Strategy per slip whose work_location_id is NULL:
        1. Aggregate ``hr.attendance.presenly_work_location_id`` counts for
           the employee in the payroll period.
        2. Aggregate ``presenly.overtime.request.work_location_id`` to
           cover employees whose attendance was WFA / not location-tagged.
        3. If exactly one location is found, assign it.
           If multiple locations are found, assign the dominant one
           (highest attendance count) and log a warning so an HR officer
           can use the "Split by Location" action if needed.
           If no location is found at all, fall back to the employee's
           primary ``work_location_id``.
    """
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})
    Slip = env['custom.payroll.slip'].sudo()
    Attendance = env['hr.attendance'].sudo()
    Overtime = env['presenly.overtime.request'].sudo()
    HrLocation = env['hr.work.location'].sudo()

    slips = Slip.search([('work_location_id', '=', False)])
    if not slips:
        _logger.info(
            'presenly_payroll 19.0.2.0: no payslips require work_location_id backfill.'
        )
        return

    _logger.info(
        'presenly_payroll 19.0.2.0: backfilling work_location_id for %d payslip(s).',
        len(slips),
    )

    backfilled_single = 0
    backfilled_dominant = 0
    backfilled_primary = 0
    skipped_no_data = 0

    for slip in slips:
        period_start, period_end = _slip_period(slip)
        if not period_start or not period_end:
            skipped_no_data += 1
            continue

        attendances = Attendance.search([
            ('employee_id', '=', slip.employee_id.id),
            ('check_in', '>=', period_start),
            ('check_in', '<=', period_end),
            ('presenly_work_location_id', '!=', False),
        ])

        loc_count = {}
        for att in attendances:
            loc_id = att.presenly_work_location_id.id
            loc_count[loc_id] = loc_count.get(loc_id, 0) + 1

        if not loc_count:
            overtime_requests = Overtime.search([
                ('employee_id', '=', slip.employee_id.id),
                ('date', '>=', period_start),
                ('date', '<=', period_end),
                ('state', '=', 'approved'),
                ('work_location_id', '!=', False),
            ])
            for req in overtime_requests:
                loc_id = req.work_location_id.id
                loc_count[loc_id] = loc_count.get(loc_id, 0) + 1

        if len(loc_count) == 1:
            loc_id = next(iter(loc_count))
            if _safe_assign(slip, loc_id):
                backfilled_single += 1
        elif len(loc_count) > 1:
            dominant_id = max(loc_count, key=loc_count.get)
            if _safe_assign(slip, dominant_id):
                backfilled_dominant += 1
                _logger.warning(
                    'presenly_payroll 19.0.2.0 backfill: payslip %s (employee %s) '
                    'had %d distinct locations in period %s; dominant location id=%s '
                    'assigned (%d attendance/overtime record(s)).',
                    slip.name,
                    slip.employee_id.name,
                    len(loc_count),
                    '%s..%s' % (period_start, period_end),
                    dominant_id,
                    loc_count[dominant_id],
                )
        else:
            primary = slip.employee_id.work_location_id
            if primary and primary.company_id == slip.company_id:
                if _safe_assign(slip, primary.id):
                    backfilled_primary += 1
            else:
                skipped_no_data += 1

    _logger.info(
        'presenly_payroll 19.0.2.0: backfill finished. '
        'single=%d dominant=%d primary_fallback=%d skipped=%d',
        backfilled_single, backfilled_dominant, backfilled_primary, skipped_no_data,
    )


def _slip_period(slip):
    if not slip.payroll_batch_id \
            or not slip.payroll_batch_id.periode_bulan \
            or not slip.payroll_batch_id.periode_tahun:
        return None, None
    try:
        year = int(slip.payroll_batch_id.periode_tahun)
        month = int(slip.payroll_batch_id.periode_bulan)
        start = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end = date(year, month, last_day)
        return start, end
    except (TypeError, ValueError):
        return None, None


def _safe_assign(slip, location_id):
    """Assign work_location_id without breaking the unique constraint."""
    existing = slip.search([
        ('payroll_batch_id', '=', slip.payroll_batch_id.id),
        ('employee_id', '=', slip.employee_id.id),
        ('work_location_id', '=', location_id),
        ('id', '!=', slip.id),
    ], limit=1)
    if existing:
        _logger.warning(
            'presenly_payroll 19.0.2.0 backfill: skipping slip %s because '
            'location %s already exists on slip %s for the same employee/batch.',
            slip.name, location_id, existing.name,
        )
        return False
    slip.write({'work_location_id': location_id})
    return True

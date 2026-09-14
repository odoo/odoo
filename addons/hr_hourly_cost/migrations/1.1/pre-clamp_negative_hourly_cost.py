import logging

from odoo.db import schema

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    if not schema.column_exists(cr, "hr_employee", "hourly_cost"):
        return
    cr.execute(
        "UPDATE hr_employee SET hourly_cost = 0 WHERE hourly_cost < 0 RETURNING id"
    )
    clamped = [row[0] for row in cr.fetchall()]
    if clamped:
        _logger.warning(
            "hr_hourly_cost 1.1: clamped a negative hourly_cost to 0 on hr.employee "
            "%s. The CHECK(hourly_cost >= 0) constraint this version adds cannot be "
            "created while such a row exists, and a constraint that fails to install "
            "is only logged.",
            clamped,
        )

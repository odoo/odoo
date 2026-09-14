import logging

from odoo.db import schema

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    if not schema.column_exists(cr, "hr_employee", "hourly_cost"):
        return
    cr.execute("UPDATE hr_employee SET hourly_cost = 0 WHERE hourly_cost IS NULL")
    if cr.rowcount:
        _logger.info(
            "hr_hourly_cost 1.2: set hourly_cost to 0 on %d hr.employee row(s) that "
            "held NULL. 1.1 dropped the field's default, so a row created under it "
            "stored NULL where every earlier row stored 0 -- two spellings of the "
            "same unset state, which the avg aggregator reads as two different "
            "numbers (NULL is excluded from the average, 0 is not).",
            cr.rowcount,
        )

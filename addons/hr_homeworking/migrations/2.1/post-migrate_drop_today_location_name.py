import logging

from odoo.db import schema

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    if schema.column_exists(cr, "hr_employee", "today_location_name"):
        cr.execute("ALTER TABLE hr_employee DROP COLUMN today_location_name")
        _logger.info(
            "hr_employee.today_location_name dropped: the column was never "
            "written, it existed so a search filter's group_by would validate"
        )

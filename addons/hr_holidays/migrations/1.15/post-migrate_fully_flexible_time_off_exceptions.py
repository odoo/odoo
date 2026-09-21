from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    if not version:
        return
    # A fully flexible employee's time off was filed under the company's
    # calendar, where the resource layer -- which reads a fully flexible
    # resource's exceptions under no calendar -- never found it.
    env = api.Environment(cr, SUPERUSER_ID, {})
    exceptions = env["resource.schedule.exception"].search(
        [
            ("holiday_id", "!=", False),
            ("calendar_id", "!=", False),
            ("holiday_id.employee_id.version_ids.resource_calendar_id", "=", False),
        ]
    )
    for exception in exceptions:
        calendar = exception.holiday_id._get_schedule_exception_calendar()
        if exception.calendar_id != calendar:
            exception.calendar_id = calendar

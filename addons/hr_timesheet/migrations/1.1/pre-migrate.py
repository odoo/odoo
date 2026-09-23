"""Move the timesheet rules off project followers.

They lived in a ``noupdate`` block and was reloaded onto
``project.project.user_has_access``. Since the ir.access conversion (base 1.97, which runs
first) each is an ``ir.access`` row under the same external id, or under the id with a
group suffix, still carrying the database's old domain; releasing their noupdate lets this
module's data load write them from ``security/ir.access.csv`` and ``security/ir_access.xml``.
"""

NAMES = (
    "timesheet_line_rule_portal_user",
    "timesheet_line_rule_user",
    "timesheet_line_rule_approver",
    "timesheet_analysis_report_user",
    "timesheet_analysis_report_approver",
)


def migrate(cr, version):
    if not version:
        return
    cr.execute(
        r"""
        UPDATE ir_model_data
           SET noupdate = false
         WHERE module = %s
           AND model = 'ir.access'
           AND (name = ANY(%s) OR name LIKE ANY(%s))
        """,
        [
            "hr_timesheet",
            list(NAMES),
            [name.replace("_", r"\_") + r"\_%" for name in NAMES],
        ],
    )

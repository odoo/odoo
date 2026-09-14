{
    "name": "Employee Presence Control",
    "version": "1.1",
    "category": "Human Resources",
    "description": """
Control Employees Presence
==========================

Marks an employee Absent when they are scheduled to work, have no approved
time off, and left no sign of activity today. Evidence of activity is:

    * a connection from one of the company's valid IP addresses
    * at least the configured number of emails sent

An HR manager can override the verdict for the day, and reach the employee by
email or SMS, log a note, or record the absence as time off.
    """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "hr",
        "hr_holidays",
        "sms",
    ],
    "data": [
        "security/sms_security.xml",
        "security/ir.model.access.csv",
        "views/hr_employee_views.xml",
        "data/mail_template_data.xml",
        "data/sms_data.xml",
        "data/ir_cron.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "hr_presence/static/src/**/*",
        ],
        "web.assets_unit_tests": [
            "hr_presence/static/tests/**/*",
        ],
    },
}

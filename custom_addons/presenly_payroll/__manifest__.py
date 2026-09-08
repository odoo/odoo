{
    'name': 'Presenly → Payroll Bridge',
    'version': '19.0.2.0.0',
    'category': 'Human Resources/Payroll',
    'summary': 'Bridges approved Presenly overtime requests into Custom Payroll slips',
    'description': """
Presenly → Payroll Bridge
=========================
Overtime on payslips (custom.payroll.slip) now comes ONLY from approved
Presenly Overtime Requests (presenly.overtime.request, state = 'approved')
within the payroll period. The legacy calculation from hr.attendance
worked hours is removed. A manual override on the slip still wins.

v19.0.2.0.0
------------
Adds multi-location support:
- Payslips now carry a `work_location_id` so a single employee working at
  several locations in one payroll period can have one slip per location.
- The wizard generator and overtime domain both filter by location.
- This migration backfills `work_location_id` on existing slips whose
  value is still NULL, based on the employee's attendance / overtime
  records in the period.
    """,
    'author': 'Presenly',
    'website': '',
    'depends': [
        'hr_payroll_custom',
        'presenly',
    ],
    'data': [
        'views/custom_payroll_slip_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
}
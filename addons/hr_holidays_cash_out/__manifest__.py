# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Leave Cash-out',
    'version': '1.0',
    'category': 'Services/Employee Hourly Cost',
    'summary': 'Leave Cash-out',
    'description': """
This module allows user to cash out his allocated time off.
============================================================================

    """,
    'depends': ['hr_holidays'],
    'data': [
        'security/hr_leave_cash_out_security.xml',
        'security/ir.model.access.csv',
        'views/hr_leave_cash_out_views.xml',
        'views/hr_leave_type_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'hr_holidays_cash_out/static/src/**/*',
        ],
    }
}

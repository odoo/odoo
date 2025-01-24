# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'India - Time Off',
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Leave Management of Indian Localization',
    'description': 'The Indian Time Off module provides additional features to the application. With it, you\'ll be able to define Sandwich Leaves on your time off type, including weekends or holidays in the duration of the employee leave\'s request.',
    'countries': ['in'],
    'depends': ['hr_holidays'],
    'auto_install': ['hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'security/l10n_in_hr_holidays_security.xml',
        'views/hr_leave_views.xml',
        'views/hr_leave_type_views.xml',
        'views/l10n_in_hr_leave_optional_holiday_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'l10n_in_hr_holidays/static/src/**/*',
        ],
    },
}

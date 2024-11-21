# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'India - Time Off',
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Leave Management of Indian Localization',
    'countries': ['in'],
    'depends': ['hr_holidays'],
    'auto_install': ['hr_holidays'],
    'data': [
        'views/hr_leave_views.xml',
        'views/hr_leave_type_views.xml',
    ],
    'license': 'LGPL-3',
}

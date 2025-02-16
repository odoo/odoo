# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Homeworking Calendar with Google Calendar',
    'version': '1.0',
    'category': 'Human Resources/Remote Work',
    'depends': ['hr_homeworking_calendar', 'google_calendar'],
    'data': [
        'data/ir_cron_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

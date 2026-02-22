# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Homeworking Calendar with Google Calendar',
    'category': 'Human Resources/Remote Work',
    'depends': ['hr_homeworking_calendar', 'google_calendar'],
    'data': [
        'data/ir_cron_data.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Recruitment - SMS',
    'version': '1.0',
    'summary': 'Mass mailing sms to job applicants',
    'description': 'Mass mailing sms to job applicants',
    'category': 'Hidden',
    'depends': ['hr_recruitment', 'sms'],
    'data': [
        'views/hr_applicant_views.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

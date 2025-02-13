# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment - Event',
    'category': 'Human Resources/Recruitment',
    'version': '1.0',
    'depends': ['event', 'hr_recruitment'],
    'data': [
        'security/ir.model.access.csv',
        'report/hr_applicant_event_report.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

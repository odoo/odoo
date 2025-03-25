# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'India - Work Entries Time Off',
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Management of work entries for sandwich leaves in india',
    'countries': ['in'],
    'depends': [
        'l10n_in_hr_holidays',
        'hr_work_entry_holidays',
    ],
    'author': 'Odoo S.A.',
    'auto_install': ['hr_work_entry_holidays'],
    'license': 'LGPL-3',
}

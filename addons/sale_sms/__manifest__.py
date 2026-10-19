# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Sale - SMS",
    'summary': "Ease SMS integration with sales capabilities",
    'description': "Ease SMS integration with sales capabilities",
    'category': 'Sales/Sales',
    'depends': ['sale', 'sms'],
    'data': [
        'security/ir.access.csv',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

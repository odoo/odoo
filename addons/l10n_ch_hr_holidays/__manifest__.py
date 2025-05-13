# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Switzerland - Time Off',
    'icon': '/account/static/description/l10n.png',
    'countries': ['ch'],
    'category': 'Human Resources/Time Off',
    'depends': ['hr_holidays'],
    'auto_install': True,
    'version': '1.0',
    'description': "Management of leaves for public holidays in Switzerland",
    'data': [
        'views/resource_calendar_leaves_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}

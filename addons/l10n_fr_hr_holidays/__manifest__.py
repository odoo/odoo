# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Time Off',
    'countries': ['fr'],
    'version': '1.0',
    'category': 'Human Resources/Time Off',
    'summary': 'Management of leaves for part-time workers in France',
    'depends': ['hr_holidays'],
    'auto_install': ['hr_holidays'],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'demo': [
        'data/l10n_fr_hr_holidays_demo.xml',
    ],
}

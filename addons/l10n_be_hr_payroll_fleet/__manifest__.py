# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgium - Payroll - Fleet',
    'category': 'Localization',
    'depends': ['l10n_be_hr_payroll', 'fleet'],
    'description': """
    """,
    'data': [
        'views/fleet_views.xml',
        'views/res_config_settings_views.xml',
        'views/hr_contract_views.xml',
    ],
    'auto_install': True,
}

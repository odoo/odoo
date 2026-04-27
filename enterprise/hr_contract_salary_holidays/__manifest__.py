# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Salary Configurator - Holidays',
    'category': 'Human Resources',
    'summary': 'Automatically creates extra time-off on contract signature',
    'depends': [
        'hr_contract_salary',
        'hr_holidays',
    ],
    'data': [
        'views/hr_contract_views.xml',
        'views/res_config_settings_views.xml',
        'data/hr_holidays_data.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}

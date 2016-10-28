# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Colombian Acounting - NIIF/Dual',
    'version': '1.0',
    'category': 'Localization',
    'description': 'Colombian NIIF chart or accounts with dual design (niif & colgaap)',
    'author': 'David Arnold (DevCO Colombia)',
    'website': 'http://www.devco.co',
    'depends': ['l10n_co'],
    'data': [
        'data/account_tag_data.xml',
        'data/l10n_co_niif_chart_data.xml',
        'data/account_chart_template_data.yml',
    ],
}

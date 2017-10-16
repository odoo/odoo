# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
# Copyright (C) 2017 KMEE INFORMATICA LTDA (https://www.kmee.com.br)


{
    'name': 'Brazilian - Accounting',
    'category': 'Localization',
    'description': """Base da contabilidade brasileira

Estrtura dos relatórios contábeis

- DRE
- Balanço Patrimonial

================================
""",
    'author': 'Odoo Brasil',
    'website': 'http://www.odoobrasil.org.br',
    'depends': ['account'],
    'data': [
        'data/account_account_type_dre_data.xml',
        'data/account_account_type_balanco_data.xml',
        'data/account_financial_report_dre_data.xml',
        'data/account_financial_report_balanco_data.xml',

        'views/account_account_type_view.xml',
        'views/account_account_template_view.xml',
        'views/account_account_view.xml',
        # 'views/account_config_settings_view.xml',
    ],
}

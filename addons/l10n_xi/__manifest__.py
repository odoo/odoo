# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Northern Ireland - Accounting',
    'version': '1.0',
    'category': 'Accounting/Localizations/Account charts',
    'description': """
This module manages accounting for Northern Ireland in Odoo.
==================================================================
Although Northern Ireland is part of the UK, there are differences in the way that Northern Ireland
trades goods with Europe due to the Northern Ireland protocol. This module includes:
    - Taxes specific to trade in goods with the European Union
    - A fiscal position for trade in goods and services with the European Union (specific to Northern Ireland)
""",
    'depends': [
        'account',
        'base_iban',
        'base_vat',
        'l10n_uk',
    ],
    'data': [
        'data/account_chart_template.xml',
        'data/account_tax_data.xml',
        'data/account_fiscal_position_template_data.xml',
        'data/account_chart_template_configure_data.xml',
    ],
    'demo': [
        'demo/demo_company.xml'
    ],
    'license': 'LGPL-3',
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Base EORI Number',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
EORI validation for Partner's EORI numbers.
===========================================
Adds validation for both EU and GB EORI Numbers.
    """,
    'author': 'XCLUDE AB',
    'website': 'https://www.xclude.se',
    'depends': ['account'],    
    'data': [
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
    ],
}

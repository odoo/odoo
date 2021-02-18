# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Base EORI Number',
    'version': '1.0',
    'category': 'Hidden/Dependency',
    'description': 'Adds field eori_number partners and EORI validation service.',
    'author': 'XCLUDE AB',
    'website': 'https://www.xclude.se',
    'depends': ['account'],    
    'data': [
        'views/res_company_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
    ],
}

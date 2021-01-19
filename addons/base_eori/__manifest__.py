# Copyright 2019-2021 XCLUDE AB (http://www.xclude.se)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
# @author Daniel Stenlöv <daniel.stenlov@xclude.se>

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

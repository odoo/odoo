# -*- coding: utf-8 -*-
{
    'name': "Partner Autocomplete",
    'summary': """
        Auto-complete partner companies' data""",
    'description': """
       Auto-complete partner companies' data
    """,
    'author': "Odoo SA",
    'category': 'Tools',
    'version': '1.0',

    'depends': ['web', 'iap'],
    'data': [
        'views/partner_autocomplete_assets.xml',
        'views/res_partner_views.xml',
        'views/res_company_views.xml',
    ],
    'qweb': [
        'static/src/xml/partner_autocomplete.xml'
    ],
    'auto_install': True,
}

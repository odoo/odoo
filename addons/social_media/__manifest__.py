# -*- coding: utf-8 -*-
{
    'name': "social_media",

    'summary': """
        Social media connectors for company settings.""",

    'description': """
        The purpose of this technical module is to provide a front for
        social media configuration for any other module that might need it.
    """,

    'author': "Odoo S.A.",
    'website': "https://wwww.odoo.com",

    'category': 'Uncategorized',
    'version': '0.1',

    'depends': ['base'],

    'data': [
        'views/res_company_views.xml',
    ],
}

# -*- coding: utf-8 -*-
{
    'name': "Social Media",

    'summary': "Social media connectors for company settings.",

    'description': """
The purpose of this technical module is to provide a front for
social media configuration for any other module that might need it.
    """,
    'category': 'Hidden',
    'version': '0.1',
    'depends': ['base'],

    'data': [
        'views/res_company_views.xml',
    ],
    'demo': [
        'demo/res_company_demo.xml',
    ],
    'license': 'LGPL-3',
}

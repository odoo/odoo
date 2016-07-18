# -*- coding: utf-8 -*-
{
    'name': "statutory_details",

    'summary': """
        This moduls has the statutory details for the contacts.""",

    'description': """
        This module has the statutory details for the contacts/companies.

        Fields Included:
            -
            -

        Views Affected:
            -
            -
    """,

    'author': "Akshay Jain",
    'website': "",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','sale'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
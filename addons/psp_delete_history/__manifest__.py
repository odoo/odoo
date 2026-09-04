# -*- coding: utf-8 -*-
{
    'name': "Delete History",

    'summary': "Record delete history",

    'description': """
-Keep History of deleted records in every models.
    """,

    'author': "Pranav PS",
    'maintainer':'Pranav P S',
    'website': "https://www.creativewe.com",
    'images': ["static/description/banner.png"],

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Base',
    'version': "16.0.1.0.0",
    'license': 'AGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_delete_history.xml',
    ],
}


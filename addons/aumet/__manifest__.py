# -*- coding: utf-8 -*-
{
    'name': "Aumet",

    'summary': """
    Custom Module for Aumet's POS
        Includes POS Scientific names and seed command for pre-defined scientific names""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Aumet",
    'website': "http://www.aumet.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/14.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Aumet',
    'version': '0.1',

    # any module necessary for this one to work correctly

    'depends': ['product', 'base', 'base_setup'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'data/aumet.scientific_name.csv',
        # 'views/aumet.xml',
        'views/views.xml',
        # 'views/templates.xml',
    ],
    # only loaded in demonstration mode

    'installable': True,
    'application': True,
}

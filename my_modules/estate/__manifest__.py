# -*- coding: utf-8 -*-
{
    'name': "Estate",

    'summary': "Estate related module",

    'description': """Long description of module's purpose""",

    'author': "Odoo-love",
    'website': "https://www.odoo.com/estate",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Estate',
    'version': '0.1',
    'license': 'LGPL-3',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'security/ir.model.access.csv',
        'views/estate_views.xml',
        'views/estate_visit.xml'
    ],
    # only loaded in demonstration mode

    'application' : True
}
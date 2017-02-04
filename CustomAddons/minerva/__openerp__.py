# -*- coding: utf-8 -*-
{
    'name': "KHF_minerva",

    'summary': """
        KHF paskaitų ir egzaminų tvarkaraščių atvaizdavimo modulis""",

    'description': """
        Long description of module's purpose
    """,

    'author': "Evaldas Grišius",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website', 'openeducat_timetable'],

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
    'application': True,
    
}
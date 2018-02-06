# -*- coding: utf-8 -*-
{
    'name': "OpenAcademy",

    'summary': """Academy module - module 26""",

    'description': """
    """,

    'author': "Odoos",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/10.0/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Academy',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'portal', 'web', 'web_kanban'],

    # always loaded
    'data': [
        'security/openacademy.xml',
        'security/ir.model.access.csv',
        'views/courses.xml',
        'views/sessions.xml',
        'views/partners.xml',
        'views/templates.xml',
    ],
    'qweb': [
        "static/src/xml/*.xml",
    ],
    # only loaded in demonstration mode
    'demo': [
        'data/partner_category_demo.xml',
        'data/partner_demo.xml',
        'data/course_demo.xml',
    ],
}

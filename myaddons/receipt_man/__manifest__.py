# -*- coding: utf-8 -*-
{
    'name': "Receipt Man",

    'summary': """
        康虎单据通""",

    'description': """
        康虎单据通用来对出入库单据的简单管理及打印
    """,

    'author': "CFSoft Stusio",
    'website': "http://www.khcloud.net",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'cfsoft',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'cfprint'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'data/ir_sequence_data.xml',
        'report/report_templates.xml',
        'report/report_view.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
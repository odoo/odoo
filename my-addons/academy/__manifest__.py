# -*- coding: utf-8 -*-
{
    'name': "Academy",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,

    'author': "My Company",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],
    'css': ['static/src/css/ab.css'],
    # always loaded
    'data': [
        'wizard/report_param_wizard.xml',
       'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'reports/teachers_report.xml',
        'reports/library_book_sql_report.xml',
        'reports/custom_report.xml',
        'views/add_button.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'qweb':[
        'static/src/xml/tree_button.xml'],
    'installable': True,
    'auto_install': False,
    'application': True,
}

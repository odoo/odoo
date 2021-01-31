# -*- coding: utf-8 -*-
{
    'name': "fastreport_odoo",

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

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
        'wizard/fastreport_create_data_template.xml',
        'views/webclient_templates.xml',
        'views/fastreport_report_menu.xml',
        'views/fastreport_iframe.xml',
        'views/fastreport_designer_view.xml',
        'views/report_xml_view.xml',
        'views/res_company_view.xml',
        'views/reportcategory.xml',
        'views/information.xml',
        'views/multiplefield.xml',
    ],
    "installable": True,
    "application": True,
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}

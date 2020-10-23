# -*- coding: utf-8 -*-
{
    'name': "l10n_de_pos_cert",

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
    'depends': ['l10n_de', 'point_of_sale'],
    'installable': True,
    'auto_install': True,
    'application': False,

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/l10n_de_pos_cert_templates.xml',
    ],
    'qweb': ['static/src/xml/OrderReceipt.xml'],
}

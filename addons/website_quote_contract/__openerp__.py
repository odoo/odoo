# -*- coding: utf-8 -*-
{
    'name': "website_quote_contract",

    'summary': """
        Website Contract and Website Quote integration""",

    'description': """
        Bridge Website Contract with Website Quote, allowing you to set
default contract templates on quotations templates. If the quotation is confirmed,
the contract is automatically created.    """,

    'author': "Odoo S.A.",
    'website': "http://www.odoo.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Sale',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website_quote', 'website_contract'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/demo.xml',
    ],
    'installable': True,
    'auto_install': True,
}
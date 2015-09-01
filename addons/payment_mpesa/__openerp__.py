# -*- coding: utf-8 -*-
{
    'name': "M-PESA Payment",

    'summary': """
        Installs Safaricom MPESA payment method on any odoo powered e-commerce website""",

    'description': """
        Customers will be able to choose MPESA mobile money payment as an option in an Odoo powered site. the site admin will need to configure the MPESA option to use\
        i.e PayBill, Buy Goods & services, send money or MPESA online payment 
    """,

    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mobile_payment'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/mpesa_aquirer.xml',
	'views/mpesa_form.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

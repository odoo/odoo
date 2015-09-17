# -*- coding: utf-8 -*-
{
    'name': "Customer Data Validation for E-commerce Site",

    'summary': """
        Validate the data entered by customer during online shopping before submitting to the server
        """,

    'description': """
        This Modules ensures that the data entered by your customer is valid before submitting to the ecommerce backend. 
	Information entered by online customer such as email, phone, billing address, shipping/delivery address are validated before submitting
	The messages returned to the form when invalid data is entered can be customised easilt to suit your preference. 
	Also the messages are translated to any language used in the website
    """,

    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",
    'images': ['static/description/main.png'],
    'price': 15,
    'currency': 'EUR',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'website',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'website_jquery_validation'],

    # always loaded
    'data': [
        # 'security/ir.model.access.csv',
        'views/validation.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

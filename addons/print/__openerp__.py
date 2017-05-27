# -*- coding: utf-8 -*-
{
    'name': 'Print Invoice',
    'summary': 'Print and Send Provider Base Module',
    'category': 'Tools',
    'version': '1.0',
    'description': """Print and Send Provider Base Module. Print and send your invoice with a Postal Provider. This required to install a module implementing a provider.""",
    'author': 'Odoo SA',
    'depends': ['base_setup', 'account'],
    'data': [
        'wizard/print_order_wizard_views.xml',
        'wizard/print_order_sendnow_wizard_views.xml',
        'views/print_provider_views.xml',
        'views/res_config_views.xml',
        'views/account_invoice_views.xml',
        'data/print_provider_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}

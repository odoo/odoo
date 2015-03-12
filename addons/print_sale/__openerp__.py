# -*- coding: utf-8 -*-
{
    'name': 'Print Sale',
    'summary': 'Print and Send Sale Orders',
    'category': 'Tools',
    'version': '1.0',
    'description': """Print and Send your Sale Order by Post""",
    'author': 'Odoo SA',
    'depends': ['print', 'sale'],
    'data': [
        'wizard/print_document_partner_wizard_views.xml',
        'views/sale_order_views.xml'
    ],
    'installable': True,
    'auto_install': True,
}

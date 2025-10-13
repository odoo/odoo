# -*- coding: utf-8 -*-
{
    'name': 'Invoicing',
    'version': '1.4',
    'summary': 'Invoices & Payments',
    'sequence': 10,
    'description': "Invoicing & Payments - Keep track of your accounting easily.",
    'category': 'Accounting/Accounting',
    'website': 'https://www.odoo.com/app/invoicing',
    'depends': ['base_setup', 'onboarding', 'product', 'analytic', 'portal', 'digest'],
    'data': [
        'security/account_security.xml',
        'security/ir.model.access.csv',
        'data/account_data.xml',
        'views/account_report.xml',
        # Add more files as needed, but keep existing paths correct
    ],
    'demo': [
        'demo/account_demo.xml',
    ],
    'installable': True,
    'application': True,
    'post_init_hook': '_account_post_init',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

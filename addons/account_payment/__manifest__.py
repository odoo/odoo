# -*- coding: utf-8 -*-

{
    'name': 'Payment - Account',
    'category': 'Accounting',
    'summary': 'Account and Payment Link and Portal',
    'version': '1.0',
    'description': """Link Account and Payment and add Portal Payment

Provide tools for account-related payment as well as portal options to
enable payment.

 * UPDATE ME
""",
    'depends': ['payment', 'account'],
    'data': [
        'views/account_invoice_views.xml',
        'views/payment_views.xml',
        'views/account_portal_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Invoicing Management',
    'version': '1.0',
    'summary': 'Send Invoices and Track Payments',
    'sequence': 30,
    'description': """
Invoicing & Payments
====================
The specific and easy-to-use Invoicing system in Odoo allows you to keep track of your accounting, even when you are not an accountant. It provides an easy way to follow up on your vendors and customers.

You could use this simplified accounting in case you work with an (external) account to keep your books, and you still want to keep track of payments. This module also offers you an easy method of registering payments, without having to encode complete abstracts of account.
    """,
    'category': 'Invoicing Management',
    'website': 'https://www.odoo.com/page/billing',
    'depends': ['account'],
    'data': [
        'views/account_menuitem_views.xml',
        'views/product_template_views.xml',
        'views/account_invoicing_templates.xml',
        'views/account_invoicing_views.xml',

    ],
    'demo': [
    ],
    'qweb': [
    ],
    'application': True,
    'uninstall_hook': 'uninstall_hook',
    'post_init_hook': 'post_init_hook',
}

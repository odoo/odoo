# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Portal Sale',
    'version': '0.1',
    'category': 'Sales',
    'complexity': 'easy',
    'description': """
This module adds a Sales menu to your portal as soon as sale and portal are installed.
======================================================================================

After installing this module, portal users will be able to access their own documents
via the following menus:

  - Quotations
  - Sale Orders
  - Delivery Orders
  - Products (public ones)
  - Invoices
  - Payments/Refunds

If online payment acquirers are configured, portal users will also be given the opportunity to
pay online on their Sale Orders and Invoices that are not paid yet. Paypal is included
by default, you simply need to configure a Paypal account in the Accounting/Invoicing settings.
    """,
    'depends': ['sale', 'portal', 'payment'],
    'data': [
        'security/portal_sale_security.xml',
        'views/sale_order_views.xml',
    ],
    'auto_install': True,
    'category': 'Hidden',
}

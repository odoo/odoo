# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Dates on Sales Order',
    'version': '1.1',
    'category': 'Sales Management',
    'description': """
Add additional date information to the sales order.
===================================================

You can add the following additional dates to a sales order:
------------------------------------------------------------
    * Requested Date (will be used as the expected date on pickings)
    * Commitment Date
    * Effective Date
""",
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sale_stock'],
    'data': ['sale_order_dates_view.xml'],
    'demo': [],
    'test': ['test/requested_date.yml'],
    'installable': True,
    'auto_install': False,
}

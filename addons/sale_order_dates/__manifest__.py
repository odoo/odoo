# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Delivery Dates on Sales Order',
    'version': '1.1',
    'category': 'Sales',
    'description': """
Manage delivery dates from sales orders.
===================================================
   This option introduces extra fields in the sales order to easily schedule product deliveries on your own: expected date, commitment date, effective date.
""",
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sale_stock'],
    'data': ['views/sale_order_views.xml'],
}

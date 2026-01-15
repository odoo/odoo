# -*- coding: utf-8 -*-
{
    'name': 'Custom Sale Panels Multiplier',
    'version': '19.0.1.0.0',
    'category': 'Sales',
    'summary': 'Add Number of Panels field in Sales Orders with impact on financial calculations',
    'description': """
        Custom Sale Panels Multiplier
        =============================
        
        This module adds "Number of Panels" field in Sales Order Lines.
        
        Features:
        ----------
        * Add "Number of Panels" field before quantity field
        * Multiply number of panels × quantity in all financial calculations
        * Impact on price, taxes, and total
        * Impact on invoices and deliveries
        * 100% safe - does not affect old data
        
        Usage:
        ----------
        1. Open a new Quotation
        2. Add a product
        3. Enter quantity (e.g.: 10)
        4. Enter number of panels (e.g.: 2)
        5. Effective quantity = 2 × 10 = 20
        6. Total price = Price × 20
        
        Notes:
        --------
        * If number of panels = 0 or empty, it will not affect calculations
        * Old data will not be affected
        * Module can be uninstalled without issues
    """,
    'author': 'Odoo Developer',
    'website': 'https://www.odoo.com',
    'depends': [
        'sale',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

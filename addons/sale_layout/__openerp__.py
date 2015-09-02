# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sale Layout',
    'version': '1.0',
    'sequence': 14,
    'summary': 'Sale Layout, page-break, subtotals, separators, report',
    'description': """
Manage your sales reports
=========================
With this module you can personnalize the sale order and invoice report with
separators, page-breaks or subtotals.
    """,
    'website': 'https://www.odoo.com/page/crm',
    'depends': ['sale', 'report'],
    'category': 'Sale',
    'data': ['views/sale_order_views.xml',
             'views/account_invoice_templates.xml',
             'views/account_invoice_views.xml',
             'views/sale_order_templates.xml',
             'views/sale_layout_templates.xml',
             'views/sale_layout_views.xml',
             'security/ir.model.access.csv'],
    'demo': ['data/sale_layout_category_data.xml'],
    'installable': True,
}

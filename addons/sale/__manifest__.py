# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Sales',
    'version': '1.1',
    'category': 'Sales',
    'summary': 'Sales internal machinery',
    'description': """
This module contains all the common features of Sales Management and eCommerce.
    """,
    'depends': ['sales_team', 'account', 'procurement'],
    'data': [
        'data/ir_sequence_data.xml',
        'data/sale_data.xml',
        'report/sale_report.xml',
        'data/mail_template_data.xml',
        'report/sale_report_views.xml',
        'report/sale_report_templates.xml',
        'report/invoice_report_templates.xml',
        'security/sale_security.xml',
        'security/ir.model.access.csv',
        'wizard/sale_make_invoice_advance_views.xml',
        'views/sale_views.xml',
        'views/sales_team_views.xml',
        'views/res_partner_views.xml',
        'views/sale_templates.xml',
        'views/sale_layout_category_view.xml',
        'views/sale_config_settings_views.xml',
    ],
    'demo': [
        'data/sale_demo.xml',
        'data/product_product_demo.xml',
    ],
    'css': ['static/src/css/sale.css'],
    'installable': True,
    'auto_install': False,
}

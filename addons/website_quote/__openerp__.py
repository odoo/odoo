# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Online Proposals',
    'category': 'Website',
    'summary': 'Send Professional Quotations',
    'website': 'https://www.odoo.com/page/quote-builder',
    'version': '1.0',
    'description': """
Odoo Sale Quote Roller
=========================

        """,
    'depends': ['website', 'sale', 'mail', 'web_tip', 'payment', 'website_portal_sale', 'website_mail'],
    'data': [
        'views/website_quote_report.xml',
        'views/website_quote_templates.xml',
        'views/sale_order_views.xml',
        'views/sale_quote_template_views.xml',
        'views/report_saleorder.xml',
        'views/report_quote.xml',
        'data/website_quote_data.xml',
        'security/ir.model.access.csv',
        'data/website_quote_tip_data.xml',
    ],
    'demo': [
        'data/website_quote_demo.xml'
    ],
    'qweb': ['static/src/xml/*.xml'],
}

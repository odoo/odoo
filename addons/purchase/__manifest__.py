# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Purchase',
    'version': '1.2',
    'category': 'Operations/Purchase',
    'sequence': 60,
    'summary': 'Purchase orders, tenders and agreements',
    'description': "",
    'website': 'https://www.odoo.com/page/purchase',
    'depends': ['account'],
    'data': [
        'security/purchase_security.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'data/purchase_data.xml',
        'report/purchase_reports.xml',
        'views/purchase_views.xml',
        'views/res_config_settings_views.xml',
        'views/product_views.xml',
        'views/res_partner_views.xml',
        'views/purchase_template.xml',
        'report/purchase_bill_views.xml',
        'report/purchase_report_views.xml',
        'data/mail_template_data.xml',
        'views/portal_templates.xml',
        'report/purchase_order_templates.xml',
        'report/purchase_quotation_templates.xml',
    ],
    'demo': [
        'data/purchase_demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}

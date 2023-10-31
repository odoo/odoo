# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Coupon",
    'summary': "Use discount coupons in different sales channels.",
    'description': """Integrate coupon mechanism in orders.""",
    'category': 'Sales',
    'version': '1.0',
    'depends': ['account'],
    'data': [
        'wizard/coupon_generate_views.xml',
        'security/ir.model.access.csv',
        'security/coupon_security.xml',
        'views/coupon_views.xml',
        'views/coupon_program_views.xml',
        'report/coupon_report.xml',
        'report/coupon_report_templates.xml',
        'data/expire_coupon_cron.xml',
    ],
    'demo': [
        'demo/coupon_demo.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}

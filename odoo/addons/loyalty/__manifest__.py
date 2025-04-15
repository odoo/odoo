# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Coupons & Loyalty',
    'summary': "Use discounts, gift card, eWallets and loyalty programs in different sales channels",
    'category': 'Sales',
    'version': '1.0',
    'depends': ['product'],
    'data': [
        'security/ir.model.access.csv',
        'security/loyalty_security.xml',
        'report/loyalty_report_templates.xml',
        'report/loyalty_report.xml',
        'data/mail_template_data.xml',
        'data/loyalty_data.xml',
        'wizard/loyalty_generate_wizard_views.xml',
        'views/loyalty_card_views.xml',
        'views/loyalty_mail_views.xml',
        'views/loyalty_program_views.xml',
        'views/loyalty_reward_views.xml',
        'views/loyalty_rule_views.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'data/loyalty_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loyalty/static/src/js/loyalty_card_list_view.js',
            'loyalty/static/src/js/loyalty_control_panel_widget.js',
            'loyalty/static/src/js/loyalty_list_view.js',
            'loyalty/static/src/scss/loyalty.scss',
            'loyalty/static/src/xml/loyalty_templates.xml',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

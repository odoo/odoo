# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Coupons & Loyalty",
    'summary': "Use discounts, gift card, eWallets and loyalty programs in different sales channels",
    'category': 'Sales',
    'version': '1.0',
    'depends': ['product', 'portal', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'security/loyalty_security.xml',
        'report/loyalty_report_templates.xml',
        'report/loyalty_report.xml',
        'data/mail_template_data.xml',
        'data/loyalty_data.xml',
        'wizard/loyalty_card_update_balance_views.xml',
        'wizard/loyalty_generate_wizard_views.xml',
        'views/loyalty_card_views.xml',
        'views/loyalty_history_views.xml',
        'views/loyalty_mail_views.xml',
        'views/loyalty_program_views.xml',
        'views/loyalty_reward_views.xml',
        'views/loyalty_rule_views.xml',
        'views/portal_templates.xml',
        'views/res_partner_views.xml',
    ],
    'demo': [
        'data/loyalty_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'loyalty/static/src/js/**/*.js',
            'loyalty/static/src/scss/*.scss',
            'loyalty/static/src/xml/*.xml',

            ('remove', 'loyalty/static/src/js/portal/**/*'),
        ],
        'web.assets_frontend': [
            'loyalty/static/src/js/portal/**/*',
            'loyalty/static/src/interactions/*',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

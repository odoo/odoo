# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Acquirer',
    'category': 'Hidden',
    'summary': 'Base Module for Payment Acquirers',
    'version': '1.0',
    'description': """Payment Acquirer Base Module""",
    'depends': ['account'],
    'data': [
        'data/account_data.xml',
        'data/payment_icon_data.xml',
        'data/payment_acquirer_data.xml',
        'data/payment_cron.xml',
        'views/payment_views.xml',
        'views/account_payment_views.xml',
        'views/account_invoice_views.xml',
        'views/payment_acquirer_onboarding_templates.xml',
        'views/payment_templates.xml',
        'views/payment_portal_templates.xml',
        'views/res_partner_views.xml',
        'security/ir.model.access.csv',
        'security/payment_security.xml',
        'wizards/payment_link_wizard_views.xml',
        'wizards/account_payment_register_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_backend': [
            # inside .
            'payment/static/src/scss/payment_acquirer.scss',
        ],
        'web.assets_frontend': [
            # after link[last()]
            'payment/static/src/scss/portal_payment.scss',
            # after link[last()]
            'payment/static/src/scss/payment_form.scss',
            # after script[last()]
            'payment/static/lib/jquery.payment/jquery.payment.js',
            # after script[last()]
            'payment/static/src/js/payment_portal.js',
            # after script[last()]
            'payment/static/src/js/payment_form.js',
            # after script[last()]
            'payment/static/src/js/payment_processing.js',
        ],
    }
}

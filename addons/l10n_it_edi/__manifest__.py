# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - E-invoicing',
    'version': '0.4',
    'depends': [
        'l10n_it',
        'account_edi_proxy_client',
    ],
    'auto_install': ['l10n_it'],
    'description': """
E-invoice implementation
    """,
    'category': 'Accounting/Localizations/EDI',
    'website': 'http://www.odoo.com/',
    'data': [
        'security/ir.model.access.csv',
        'data/invoice_it_template.xml',
        'data/invoice_it_simplified_template.xml',
        'data/ir_cron.xml',
        'data/account.account.tag.csv',
        'data/l10n_it.document.type.csv',
        'views/res_config_settings_views.xml',
        'views/l10n_it_view.xml',
        'views/portal_address_templates.xml',
        'views/report_invoice.xml',
        'views/account_payment_method.xml',
        'views/l10n_it_document_type.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'l10n_it_edi/static/src/js/address.js',
        ],
        'web.assets_tests': [
            'l10n_it_edi/static/tests/tours/*.js',
        ],
    },
    'demo': [
        'data/account_invoice_demo.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'post_init_hook': '_l10n_it_edi_create_param',
}

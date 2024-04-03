# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - E-invoicing',
    'icon': '/l10n_it/static/description/icon.png',
    'version': '0.3',
    'depends': [
        'l10n_it',
        # Although account_edi is a dependency of account_edi_proxy_client,
        # it is here because it's in the auto-install
        'account_edi',
        'account_edi_proxy_client',
    ],
    'auto_install': ['l10n_it', 'account_edi'],
    'author': 'Odoo',
    'description': """
E-invoice implementation
    """,
    'category': 'Accounting/Localizations/EDI',
    'website': 'http://www.odoo.com/',
    'data': [
        'security/ir.model.access.csv',
        'data/account_edi_data.xml',
        'data/invoice_it_template.xml',
        'data/invoice_it_simplified_template.xml',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'views/l10n_it_view.xml',
        ],
    'demo': [
        'data/account_invoice_demo.xml',
    ],
    'post_init_hook': '_l10n_it_edi_post_init',
    'license': 'LGPL-3',
}

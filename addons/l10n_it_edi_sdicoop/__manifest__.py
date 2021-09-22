# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Italy - E-invoicing (SdiCoop)',
    'version': '0.3',
    'depends': [
        'l10n_it_edi',
        'account_edi',
        'account_edi_proxy_client',
    ],
    'author': 'Odoo',
    'description': """
E-invoice implementation for Italy with the web-service. Ability to send and receive document from SdiCoop. Files sent by SdiCoop are first stored on the proxy
and then fetched by this module.
    """,
    'category': 'Accounting/Localizations/EDI',
    'website': 'http://www.odoo.com/',
    'data': [
        'data/cron.xml',
        'views/l10n_it_view.xml',
        'views/res_config_settings_views.xml',
    ],
    'post_init_hook': '_disable_pec_mail_post_init',
    'license': 'LGPL-3',
}

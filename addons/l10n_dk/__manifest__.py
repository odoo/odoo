# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Denmark - Accounting',
    'icon': '/account/static/description/l10n.png',
    'countries': ['dk'],
    'version': '1.3',
    'author': 'Odoo House ApS, VK DATA ApS, FlexERP ApS',
    'website': 'https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations.html',
    'category': 'Accounting/Localizations/Account Charts',
    'description': """

Localization Module for Denmark
===============================

This is the module to manage the **accounting chart for Denmark**. Cover both one-man business as well as I/S, IVS, ApS and A/S
Also provides Nemhandel registration and invoice sending throught the Odoo Access Point

    """,
    'depends': [
        'base_iban',
        'base_vat',
        'account',
        'account_edi_proxy_client',
        'account_edi_ubl_cii',
    ],
    'auto_install': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'data/account_tax_report_data.xml',
        'data/account.account.tag.csv',
        'data/cron.xml',
        'data/nemhandel_onboarding_tour.xml',
        'views/account_journal_views.xml',
        'views/account_move_views.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_partner_views.xml',
        'wizard/nemhandel_registration_views.xml',
    ],
    'demo': [
        'demo/demo_company.xml',
        'demo/nemhandel_mode_demo.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_dk/static/src/components/**/*',
            'l10n_dk/static/src/tours/nemhandel_onboarding.js',
        ],
    },
    'license': 'LGPL-3',
    'pre_init_hook': '_pre_init_nemhandel',
    'uninstall_hook': 'uninstall_hook',
}

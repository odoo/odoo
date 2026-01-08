# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Peppol",
    'summary': "This module is used to send/receive documents with PEPPOL",
    'description': """
- Register as a PEPPOL participant
- Send and receive documents via PEPPOL network in Peppol BIS Billing 3.0 format
    """,
    'category': 'Accounting/Accounting',
    'version': '1.2',
    'countries': [
        # !!! KEEP ALIGNED WITH ACCOUNT/MODELS/COMPANY.PEPPOL_DEFAULT_COUNTRIES
        'at', 'be', 'ch', 'cy', 'cz', 'de', 'dk', 'ee', 'es', 'fi',
        'fr', 'gr', 'ie', 'is', 'it', 'lt', 'lu', 'lv', 'mt', 'nl',
        'no', 'pl', 'pt', 'ro', 'se', 'si',
    ],
    'depends': [
        'account_edi_proxy_client',
        'account_edi_ubl_cii',
    ],
    'external_dependencies': {
        'python': ['phonenumbers'],
        'apt': {
            'phonenumbers': 'python3-phonenumbers',
        },
    },
    'data': [
        'data/cron.xml',
        'data/mail_templates_email_layouts.xml',
        'data/res_partner_data.xml',
        'security/ir.model.access.csv',
        'views/account_move_views.xml',
        'views/account_portal_templates.xml',
        'views/peppol_authentication_views.xml',
        'views/res_partner_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/peppol_registration_views.xml',
        'wizard/peppol_config_wizard.xml',
    ],
    'demo': [
        'demo/account_peppol_demo.xml',
    ],
    'post_init_hook': '_account_peppol_post_init',
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'account_peppol/static/src/components/**/*',
            'account_peppol/static/src/css/**/*',
        ],
        'web.assets_frontend': [
            'account_peppol/static/src/interactions/*',
        ],
    },
    'auto_install': ['account_edi_ubl_cii'],  # auto-install when account_edi_ubl_cii AND one company exists in countries above
}

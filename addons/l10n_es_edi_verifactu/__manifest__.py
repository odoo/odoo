# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spain - Veri*Factu',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': "Module for sending Spanish Veri*Factu XML to the AEAT",
    'website': "https://www.odoo.com/documentation/latest/applications/finance/fiscal_localizations/spain.html#veri-factu",
    'depends': ['l10n_es'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_move_reversal_views.xml',
        'views/account_move_views.xml',
        'views/account_tax_views.xml',
        'views/certificate_certificate_views.xml',
        'views/l10n_es_edi_verifactu_document_views.xml',
        'views/report_invoice.xml',
        'views/res_company_views.xml',
        'views/res_config_settings_views.xml',
        'data/ir_cron.xml',
    ],
    'demo': [
        'demo/demo_certificate.xml',
        'demo/demo_company.xml',
    ],
    'post_init_hook': '_l10n_es_edi_verifactu_post_init_hook',
    'assets': {
        'web.assets_backend': [
            'l10n_es_edi_verifactu/static/src/css/warning.scss',
        ],
    },
    'installable': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Spain - Veri*Factu',
    'version': '1.0',
    'category': 'Accounting/Localizations/EDI',
    'summary': "Module for sending Spanish Veri*Factu XML to the AEAT",
    'depends': ['l10n_es', 'l10n_es_edi_facturae'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/account_move_send_views.xml',
        'views/account_move_views.xml',
        'views/l10n_es_edi_verifactu_certificate_views.xml',
        'views/l10n_es_edi_verifactu_document_views.xml',
        'views/report_invoice.xml',
        'views/res_config_settings_views.xml',
        'views/verifactu_templates.xml',
        'data/ir_cron.xml',
    ],
    'demo': ['demo/demo_certificate.xml'],
    'assets': {
        'web.assets_backend': [
            'l10n_es_edi_verifactu/static/src/css/warning.scss',
        ],
    },
    'installable': True,
    'license': 'LGPL-3',
}

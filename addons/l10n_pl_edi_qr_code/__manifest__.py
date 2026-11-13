{
    'name': 'Poland KSeF QR Codes and Offline Mode',
    'category': 'Accounting/Localizations',
    'summary': 'KSeF invoice visualizations, QR codes, and Offline24 mode',
    'depends': ['l10n_pl_edi'],
    'data': [
        'views/report_invoice.xml',
        'views/offline_account_move_views.xml',
        'views/res_config_settings_views.xml',
        'data/ir_cron_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_pl_edi_qr_code/static/src/components/offline_actions/offline_actions.js',
            'l10n_pl_edi_qr_code/static/src/components/offline_actions/offline_actions.xml',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}

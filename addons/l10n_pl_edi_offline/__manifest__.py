{
    'name': 'Poland KSeF Offline24',
    'category': 'Accounting/Localizations',
    'summary': 'Issue invoices in the KSeF Offline24 mode when KSeF is unavailable',
    'description': """
Offline24 mode for the Polish KSeF e-invoicing.

When the online sending of an invoice to KSeF fails for a technical reason (KSeF unreachable, timeout,
server error), the invoice is issued in Offline24 if an offline certificate is configured: its KSeF XML
is frozen, its PDF gets the KOD I and KOD II (certificate) QR codes, and a scheduled action submits it to
KSeF once KSeF is available again, following the availability announcements of KSeF.
""",
    'depends': ['l10n_pl_edi'],
    'data': [
        'views/report_invoice.xml',
        'views/offline_account_move_views.xml',
        'views/res_config_settings_views.xml',
        'data/ir_cron_data.xml',
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

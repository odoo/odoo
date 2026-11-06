{
    'name': 'Polish E-Invoicing Batch Download',
    'category': 'Accounting/Localizations',
    'summary': 'Download the KSeF vendor bills in batches',
    'description': """
Downloads the vendor bills received in KSeF in batches, one encrypted ZIP per
timeframe, instead of one by one: the single-invoice download is limited to 64
invoices an hour.

Opt-in: enable "KSeF batch download" in the Accounting settings.
""",
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron_data.xml',
        'views/l10n_pl_edi_batch_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'depends': ['l10n_pl_edi'],
    'auto_install': ['l10n_pl_edi'],
    'license': 'LGPL-3',
}

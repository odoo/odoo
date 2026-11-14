{
    'name': 'Polish E-Invoicing Batch Download',
    'category': 'Accounting/Localizations',
    'summary': 'Download the KSeF vendor bills in batches',
    'description': """
Downloads the vendor bills received in KSeF in batches, one encrypted ZIP per
timeframe, instead of one by one: the single-invoice download is limited to 64
invoices an hour.
""",
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'data/ir_cron_data.xml',
        'views/res_config_settings_views.xml',
    ],
    'depends': ['l10n_pl_edi'],
    'auto_install': ['l10n_pl_edi'],
    'license': 'LGPL-3',
}

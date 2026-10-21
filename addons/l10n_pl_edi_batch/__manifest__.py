{
    'name': 'Polish E-Invoicing Batch Download',
    'category': 'Accounting/Localizations',
    'summary': 'Uses a batch download mechanism for FA(3) electronic invoices in Poland via KSeF',
    'description': """Uses a batch download mechanism for FA(3) electronic invoices in Poland via KSeF.""",
    'data': [
        'security/ir.model.access.csv',
        'views/l10n_pl_edi_batch_views.xml'
    ],
    'demo': [],
    'assets': {},
    'depends': ['l10n_pl_edi'],
    'auto_install': ['l10n_pl_edi'],
    'license': 'LGPL-3',
}

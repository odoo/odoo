{
    'name': "Türkiye - Nilvera Aliases",
    'category': 'Accounting/Accounting',
    'description': """
Segregates customer electronic mailboxes (aliases) on Nilvera by document type
(Invoice vs DespatchAdvice) when both E-Invoice and E-Dispatch are installed.
    """,
    'depends': [
        'l10n_tr_nilvera_einvoice',
        'l10n_tr_nilvera_edispatch',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

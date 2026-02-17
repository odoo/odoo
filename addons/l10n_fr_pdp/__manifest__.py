{
    'name': 'France - PDP',
    'version': '1.0',
    'description': """
France - PDP
================================

This module will allow sending and receiving B2B invoices
    """,
    'category': 'Accounting/Localizations/EDI',
    'depends': [
        'l10n_fr',
        'account_edi_proxy_client',
        'account_edi_ubl_cii',
    ],
    'data': [],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}

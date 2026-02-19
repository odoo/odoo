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
    'data': [
        'data/ubl_en16931_template.xml',
        'data/ubl_en16931_extended_template.xml',
        'data/cii_france_cius_template.xml',
        'data/cii_france_cius_extended_template.xml',
    ],
    'auto_install': True,
    'installable': True,
    'license': 'OEEL-1',
}

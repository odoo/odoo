# -*- coding: utf-8 -*-
{
    'name': 'Norway - E-Invoicing (EHF 3)',
    'icon': '/l10n_no/static/description/icon.png',
    'version': '0.1',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'E-Invoicing, Universal Business Language (EHF 3)',
    'description': """
EHF 3 is the Norwegian implementation of EN 16931 norm.
    """,
    'depends': ['l10n_no', 'account_edi_ubl_bis3'],
    'data': [
        'data/account_edi_data.xml',
        'data/ehf_3_template.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

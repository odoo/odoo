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
    'depends': ['l10n_no', 'account_edi_ubl'],
    'data': [
        'data/ubl_no_templates_common.xml',
        'data/ubl_no_templates_invoice.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

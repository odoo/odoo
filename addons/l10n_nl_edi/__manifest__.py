# -*- coding: utf-8 -*-
{
    'name': 'Netherlands - E-Invoicing (NLCIUS 1.0.3)',
    'icon': '/l10n_nl/static/description/icon.png',
    'version': '0.1',
    'category': 'Accounting/Localizations/EDI',
    'summary': 'E-Invoicing, Universal Business Language (NLCIUS 1.0.3), nlc',
    'description': """
NLCIUS is the Dutch implementation of EN 16931 norm. Both for UBL and UN / CEFACT XML CII.
    """,
    'depends': ['l10n_nl', 'account_edi_ubl_bis3'],
    'data': [
        'data/account_edi_data.xml',
        'data/nlcius_template.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'LGPL-3',
}

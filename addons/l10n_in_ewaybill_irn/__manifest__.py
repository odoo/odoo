# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': """Indian - E-waybill through IRN""",
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_in_ewaybill',
        'l10n_in_edi'
    ],
    'description': """
Indian - E-waybill through IRN
====================================
This module enables to generate E-waybill through IRN.
    """,
    'data': [
        'views/l10n_in_ewaybill_views.xml'
    ],
    'auto_install': True,
    'license': 'LGPL-3',
}

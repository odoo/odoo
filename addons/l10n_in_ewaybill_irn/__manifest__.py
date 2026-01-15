# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': """Indian - E-waybill thru IRN""",
    'category': 'Accounting/Localizations',
    'depends': [
        'l10n_in_ewaybill',
        'l10n_in_edi'
    ],
    'description': """
Indian - E-waybill thru IRN
====================================
This module enables to generate E-waybill through IRN.
    """,
    'data': [
        'views/l10n_in_ewaybill_views.xml',
        'report/ewaybill_report.xml',
    ],
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

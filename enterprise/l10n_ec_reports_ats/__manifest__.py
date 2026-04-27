# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Ecuador - ATS Report',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'author': 'TRESCLOUD',
    'description': """
        ATS Report for Ecuador
    """,
    'depends': [
        'l10n_ec_edi',
        'l10n_ec_reports',
    ],
    'data': [
        'data/ats_report.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OPL-1',
}

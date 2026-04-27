# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Lithuanian Standard Audit File for Tax',
    'version': '1.0',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Lithuanian SAF-T is standard file format for exporting various types of accounting transactional data using the XML format.
The XSD version used is v2.01 (since 2019). It is the latest one used by the Lithuanian Authorities.
The first version of the SAF-T Financial is limited to the general ledger level including customer and supplier transactions.
Necessary master data is also included.
    """,
    'depends': [
        'l10n_lt', 'account_saft',
    ],
    'data': [
        'data/saft_report.xml',
    ],
    'license': 'OEEL-1',
    'auto_install': True,
}

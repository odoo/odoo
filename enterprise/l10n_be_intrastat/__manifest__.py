# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Intrastat Declaration',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Generates Intrastat XML report for declaration
Based on invoices.
Adds the possibility to specify the origin country of goods and the partner VAT in the Intrastat XML report.
    """,
    'depends': ['l10n_be', 'account_intrastat'],
    'data': [
        'data/code_region_data.xml',
        'data/intrastat_export.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

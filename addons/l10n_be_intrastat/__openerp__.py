# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Intrastat Declaration',
    'version': '1.0',
    'category': 'Localization',
    'description': """
Generates Intrastat XML report for declaration
Based on invoices.
    """,
    'depends': ['report_intrastat', 'sale_stock', 'account_accountant', 'l10n_be'],
    'data': [
        'data/regions.xml',
        'data/report.intrastat.code.csv',
        'data/transaction.codes.xml',
        'data/transport.modes.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
        'l10n_be_intrastat.xml',
        'wizard/l10n_be_intrastat_xml_view.xml',
    ],
    'installable': True,
}

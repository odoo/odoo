# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Belgian Intrastat Declaration',
    'category': 'Localization',
    'description': """
Generates Intrastat XML report for declaration
Based on invoices.
    """,
    'depends': ['report_intrastat', 'sale_stock', 'account_accountant', 'l10n_be'],
    'data': [
        'data/l10n_be_intrastat_chart_data.xml',
        'data/report.intrastat.code.csv',
        'data/l10n_be_intrastat_transaction_codes_data.xml',
        'data/l10n_be_intrastat_transport_modes_data.xml',
        'security/l10n_be_intrastat_security.xml',
        'security/ir.model.access.csv',
        'views/l10n_be_intrastat_view.xml',
        'wizard/l10n_be_intrastat_declaration_view.xml',
    ],
}

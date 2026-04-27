# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Germany - Accounting Reports',
    'version': '1.1',
    'category': 'Accounting/Localizations/Reporting',
    'description': """
Accounting reports for Germany
Contains Balance sheet, Profit and Loss, VAT and Partner VAT reports
Also adds DATEV export options to general ledger
    """,
    'depends': [
        'l10n_de', 'account_reports'
    ],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_and_loss.xml',
        'data/ec_sales_list_report.xml',
        'data/account_report_tax_report.xml',
        'views/res_config_settings_view.xml',
        'views/l10n_de_report_views.xml',
        'data/datev_document_metadata_export.xml',
        'data/report_export_template.xml',
    ],
    'installable': True,
    'post_init_hook': '_l10n_de_reports_post_init',
    'auto_install': ['l10n_de', 'account_reports'],
    'license': 'OEEL-1',
}

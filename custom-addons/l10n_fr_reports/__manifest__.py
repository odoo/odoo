# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'France - Accounting Reports',
    'countries': ['fr'],
    'version': '1.2',
    'description': """
Accounting reports for France
================================

This module also allows exporting the French vat report and send it to the DGFiP, an OGA or an expert accountant.

It adds a new button "EDI VAT" on the French vat report and a new menu item "EDI exports" (below "Reporting",
in the "Statement Reports" section).
    """,
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_fr', 'account_reports'],
    'data': [
        'data/balance_sheet.xml',
        'data/profit_loss.xml',
        'data/intermediate_management_balances.xml',
        'data/tax_report.xml',
        'data/cron.xml',
        'data/template.xml',
        'security/ir.model.access.csv',
        'views/res_config_settings_views.xml',
        'views/account_journal_dashboard_view.xml',
        'views/account_report_async_export_view.xml',
        'wizard/l10n_fr_send_vat_report_wizard.xml',
    ],
    'auto_install': ['l10n_fr', 'account_reports'],
    'installable': True,
    'license': 'OEEL-1',
}

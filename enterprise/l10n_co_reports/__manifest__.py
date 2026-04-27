# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (C) David Arnold (XOE Solutions).
# Author        David Arnold (XOE Solutions), dar@xoe.solutions
# Co-Authors    Juan Pablo Aries (devCO), jpa@devco.co
#               Hector Ivan Valencia Muñoz (TIX SAS)
#               Nhomar Hernandez (Vauxoo)
#               Humberto Ochoa (Vauxoo)

{
    'name': 'Colombian - Accounting Reports',
    'version': '1.1',
    'description': """
Accounting reports for Colombia
================================
    """,
    'author': 'David Arnold (XOE Solutions)',
    'category': 'Accounting/Localizations/Reporting',
    'depends': ['l10n_co', 'account_reports'],
    'data': [
        'security/ir.model.access.csv',
        'data/l10n_co_reports.xml',
        'data/l10n_co_reports_ica.xml',
        'data/l10n_co_reports_iva.xml',
        'data/l10n_co_reports_fuente.xml',
        'data/profit_loss_pymes.xml',
        'data/balance_sheet_pymes.xml',
        'data/l10n_co_reports_libro_diario.xml',
        'data/l10n_co_reports_libro_inv_blc.xml',
        'wizard/retention_report_views.xml',
        'report/certification_report_templates.xml',
        'report/libro_diario_report_templates.xml',
    ],
    'auto_install': ['l10n_co', 'account_reports'],
    'installable': True,
    'website': 'https://xoe.solutions',
    'license': 'OEEL-1',
}

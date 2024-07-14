# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    "name": "Indian - GSTR India eFiling",
    "countries": ["in"],
    "version": "1.0",
    "description": """
GST return filing using IAP
================================

** GSTR-1: Send and view summary report
** GSTR-2B: matching
** GSTR-3B: view report
    """,
    "category": "Accounting/Localizations/Reporting",
    "depends": ["l10n_in_reports", "l10n_in_edi"],
    "data": [
        "data/service_cron.xml",
        "security/ir.model.access.csv",
        "views/gst_return_period.xml",
        "views/account_move_views.xml",
        "views/res_config_settings.xml",
    ],
    "demo": [
        "demo/demo_company.xml",
    ],
    "auto_install": ['l10n_in_reports'],
    "installable": True,
    "license": "OEEL-1",
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OCA Thai Translations (OD19)",
    "version": "19.0.1.0.0",
    "category": "Localization",
    "summary": "Thai translation overlay for third-party OCA modules",
    "author": "Custom",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mis_builder",
        "mis_builder_cash_flow",
        "account_analytic_tag",
        "account_ebitda_report",
        "account_reconcile_analytic_tag",
    ],
    "post_load": "post_load",
    "installable": True,
    "application": False,
    "auto_install": True,
}

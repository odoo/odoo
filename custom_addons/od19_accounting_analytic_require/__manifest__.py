# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    "name": "OD19 Accounting Analytic Require",
    "version": "19.0.1.0.0",
    "summary": "Force analytic account on journal items for specified accounts",
    "author": "OD19",
    "category": "Accounting",
    "depends": ["account", "analytic"],
    "data": [
        "security/ir.model.access.csv",
        "views/res_company_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "application": False,
    "license": "LGPL-3",
    "icon": "/od19_accounting_analytic_require/static/description/icon.svg",
}

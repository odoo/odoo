{
    "name": "OD19 Accounting Reporting",
    "version": "19.0.2.1.0",
    "author": "TRAE",
    "depends": [
        "account",
        "sale_management",
        "od19_sales_billing_evidence",
        "od19_accounting_operational_closure",
        "od19_dashboard",
        "od19_accounting_cheque",
        "od19_accounting_petty_cash",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/accounting_reporting_security.xml",
        "views/account_menu_overrides.xml",
        "views/report_accounting_operational_closure_views.xml",
        "data/finance_control_dashboard_data.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_accounting_reporting/static/description/icon.svg",
}

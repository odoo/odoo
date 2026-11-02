{
    "name": "OD19 Accounting Operational Closure",
    "version": "19.0.1.0.0",
    "author": "TRAE",
    "depends": [
        "account",
        "sale_management",
        "od19_purchase_procurement_core",
        "od19_sales_billing_evidence",
        # The AP UAT business-flow test (P1-T10) exercises the Prepare->Approve
        # gate together with the PO -> receipt -> bill closure, so the payable
        # control gate module is a declared dependency of this closure module.
        "od19_accounting_payment_voucher_reports",
    ],
    "data": [
        "views/sale_order_views.xml",
        "views/purchase_order_views.xml",
        "views/account_move_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
    "icon": "/od19_accounting_operational_closure/static/description/icon.svg",
}

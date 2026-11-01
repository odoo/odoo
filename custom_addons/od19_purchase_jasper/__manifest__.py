{
    "name": "OD19 Purchase - Jasper Print Forms",
    "author": "OD19",
    "version": "19.0.1.0.0",
    "category": "Purchase",
    "summary": "Jasper print forms for the Purchase domain (Purchase Order Form, "
    "RFQ, purchase-request-linked order and the purchase reporting set)",
    "depends": [
        "purchase",
        "purchase_stock",
        "purchase_request",
        "base_tier_validation",
        "od19_purchase_terms",
        "od19_reporting_jasper",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizard/purchase_order_form_views.xml",
        "wizard/requests_for_quotation_form_views.xml",
        "wizard/po_purchase_request_form_views.xml",
        "wizard/purchase_order_period_report_views.xml",
        "wizard/purchase_order_outstanding_report_views.xml",
        "wizard/received_purchase_order_period_report_views.xml",
    ],
    "installable": True,
    "license": "LGPL-3",
}

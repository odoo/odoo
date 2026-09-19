{
    "name": "Documents Compliance",
    "version": "19.0.1.14.1",
    "category": "Productivity/Documents",
    "summary": "Document compliance management with expiration tracking",
    "description": """
Documents Compliance
====================

Compliance tracking for the Documents app, per document type. The type itself,
and whether and when a document expires, belong to ``document``; this module
adds the verdict layer on top.

* document types with default validity periods, renewal requirements and
  instructions, each scoped to the kind of record it is required of
* mandatory versus optional types
* an expiration state per document (valid, expiring soon, expired) driven by
  its date alone, and a compliance verdict per document (compliant,
  non-compliant, not applicable) driven by its type
* expiration tracking with per-type notification days (``30,7,1`` by
  default), recipients and scheduled activities
* verification and renewal from the document's details panel
* a per-entity compliance dashboard: percentage, and counts of missing,
  expired and expiring document types

Counts exist at both levels. A document type carries totals over its own
documents, and the compliance report aggregates per entity -- partner,
employee or vehicle -- against only the mandatory types that apply to that
kind of record.

Notifications are scheduled as activities on the document. The module sends
no email.
""",
    "author": "AgroMarin",
    "website": "https://www.agromarin.mx",
    "license": "LGPL-3",
    "depends": [
        "document",
        "mixin_report_sql",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/document_compliance_security.xml",
        "data/ir_cron_data.xml",
        "views/document_type_views.xml",
        "views/document_document_views.xml",
        "reports/document_compliance_report_views.xml",
        "views/document_compliance_menus.xml",
    ],
    "demo": [
        "demo/document_document_demo.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "document_compliance/static/src/components/document_details_panel/document_details_panel_patch.js",
            "document_compliance/static/src/components/document_details_panel/document_details_panel_patch.xml",
        ],
    },
}

# Copyright 2026 TRAE
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl).

{
    "name": "OD19 Document Hub",
    "version": "19.0.1.0.0",
    "category": "Document Management",
    "summary": "ศูนย์กลาง metadata หมวด และการค้นหาเอกสารแนบ (ir.attachment)",
    "author": "TRAE",
    "license": "LGPL-3",
    "depends": ["base", "mail", "hr", "od19_thai_font_support"],
    "pre_init_hook": "pre_init_hook",
    "data": [
        "security/od19_document_hub_security.xml",
        "security/ir.model.access.csv",
        "data/od19_document_category_data.xml",
        "views/od19_document_category_views.xml",
        "views/od19_document_retention_policy_views.xml",
        "views/ir_attachment_views.xml",
        "views/od19_document_hub_menus.xml",
    ],
    "installable": True,
    "application": True,
    "auto_install": False,
}

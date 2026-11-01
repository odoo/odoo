{
    "name": "OD19 Approval Center",
    "summary": "Config-driven, view-only approval visibility across modules",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "author": "The Auto-Info Co., Ltd.",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/od19_approval_security.xml",
        "security/ir.model.access.csv",
    ],
    "post_init_hook": "post_init_hook",
    "installable": True,
    "application": True,
    "auto_install": False,
}

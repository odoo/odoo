{
    "name": "Phone Numbers Validation",
    "version": "2.1",
    "category": "Hidden",
    "sequence": 9999,
    "summary": "Validate and format phone numbers",
    "description": """
Phone Numbers Validation
========================

This module adds the feature of validation and formatting phone numbers
according to a destination country.

It also adds phone blacklist management through a specific model storing
blacklisted phone numbers.

It adds mixin.mail.thread.phone mixin that handles sanitation and blacklist of
records numbers. """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
    ],
    "external_dependencies": {
        "python": [
            "phonenumbers",
        ],
        "apt": {
            "phonenumbers": "python3-phonenumbers",
        },
    },
    "data": [
        "security/ir.access.csv",
        "views/phone_blacklist_views.xml",
        "views/res_partner_views.xml",
        "wizards/phone_blacklist_remove_view.xml",
        "views/phone_validation_menus.xml",
    ],
    "auto_install": True,
}

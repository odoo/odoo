{
    "name": "Base Order Management",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "Foundation mixin for all order types",
    "description": """
Base Order Management
=====================

This module provides foundational mixins that consolidate common patterns
across all order types (sale, purchase, manufacturing, rental, etc.).

Key Features:
-------------
* **Order Mixins**: Standardized field naming, state machine, workflow logic
* Extensible validation framework
* Common compute methods for currency, partners, etc.
* Consistent workflow actions (confirm, cancel, lock/unlock)

Design Goals:
-------------
* Eliminate code duplication across order modules
* Provide clean extension points for customization
* Make order behavior consistent and predictable
* Improve code readability and maintainability

Field Naming Standards:
-----------------------
* Booleans: `is_locked`, `is_sent`, `is_printed`
* Counts: `send_count`, `print_count`
* No abbreviations: `quantity` not `qty`
* Symmetric naming across all order types

This module is part of an aggressive refactoring initiative for Odoo 19+ with
no backward compatibility constraints.
    """,
    "author": "Odoo Community",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "depends": [
        "base",
        "mail",
        "portal",
        "account",
        "stock",
    ],
    "data": [],
    "installable": True,
    "application": False,
    "auto_install": False,
}

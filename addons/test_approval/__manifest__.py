{
    "name": "Test - Base Approval",
    "version": "19.0.1.3.0",
    "category": "Hidden/Tests",
    "summary": "Concrete consumer of mixin.approval, for its tests",
    "description": """
Test - Base Approval
====================

``approval.test.document`` is the model ``mixin.approval`` is exercised
against: it implements every hook the mixin delegates to the source document
and records what it was called with. It lives here rather than in ``approval``
so that no customer database carries its table, and it deliberately ships no
``ir.access`` row -- the tests reach it as superuser or as a manager, and
a plain internal user must not reach it at all.
    """,
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "approval",
        "approval_automation",
    ],
}

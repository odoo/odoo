{
    "name": "Approvals",
    "version": "19.0.1.0.0",
    "category": "Human Resources/Approvals",
    "sequence": 190,
    "summary": "Raise, review and configure approval requests from one application",
    "description": """
Approvals
=========

The application over the approval engine: the Approvals menu, the generic
request categories people raise by hand (Business Trip, Borrow Items,
Procurement, ...) and their demo.

``approval`` is infrastructure. ``hr``, ``website_slides``, ``web_studio`` and
every module adopting ``mixin.approval`` depend on it, so an application tile
and eight request categories in the engine appeared on every database that
installed any of them. The engine keeps the models, security, decision ledger
and the forms an approver decides from; this module is what a company installs
when it wants approvals as a product.

It also carries the form a person fills to raise a request by hand: which fields
a category asks for, templates, document requirements, the checks at confirm,
autofill and clone defaults. A document's request fills no form, so the engine
routes and decides without one.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "approval",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/ir_rule.xml",
        "views/approval_category_views.xml",
        "views/approval_request_views.xml",
        "views/approval_template_views.xml",
        "views/approval_document_requirement_views.xml",
        "views/approval_request_template.xml",
        "data/approval_category_data.xml",
        "views/approvals_menuitem_views.xml",
    ],
    "demo": [
        "demo/00_approval_users_demo.xml",
        "demo/01_approval_groups_demo.xml",
        "demo/approval_demo.xml",
    ],
    "assets": {
        "web.assets_tests": [
            "approval_app/static/tests/tours/**/*",
        ],
    },
    "application": True,
    "pre_init_hook": "_pre_init_refuse_to_reset_the_engine_shell",
}

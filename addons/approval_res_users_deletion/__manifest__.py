{
    "name": "Account Deletion Approvals",
    "version": "19.0.1.0.0",
    "category": "Hidden",
    "summary": "A portal account deletion is decided through the approval engine",
    "description": """
Account Deletion Approvals
==========================

Where the approval engine is installed, a portal user asking for their account
to be deleted raises an approval request: who asked, when, and who let it
through are recorded, and the deletion cron removes only the accounts whose
request was approved. The shipped category approves self-service requests
automatically, so behaviour is unchanged until an administrator archives that
rule and puts a review step in its place.

A bridge rather than a dependency of ``base`` on the engine, on purpose: the
deletion queue is base's, the engine is optional, and a database that never had
``approval`` keeps its queue as it was.
""",
    "author": "AgroMarin",
    "license": "LGPL-3",
    "depends": [
        "approval",
    ],
    "data": [
        "data/approval_category_data.xml",
    ],
    "auto_install": True,
}

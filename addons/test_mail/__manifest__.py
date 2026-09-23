{
    "name": "Mail Tests",
    "version": "1.0",
    "category": "Hidden",
    "sequence": 9876,
    "summary": "Mail Tests: performances and tests specific to mail",
    "description": """This module contains tests related to mail. Those are
present in a separate module as it contains models used only to perform
tests independently to functional aspects of other models. """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "test_orm",
    ],
    "data": [
        "security/ir.access.csv",
        "data/data.xml",
        "data/mail_template_data.xml",
        "data/subtype_data.xml",
    ],
    "assets": {
        "web.assets_unit_tests": [
            "test_mail/static/tests/**/*",
        ],
        "web.assets_tests": [
            "test_mail/static/tests/tours/*",
        ],
    },
}

{
    "name": "SMS Tests",
    "version": "1.0",
    "category": "Hidden",
    "sequence": 9876,
    "summary": "SMS Tests: performances and tests specific to SMS",
    "description": """This module contains tests related to SMS. Those are
present in a separate module as it contains models used only to perform
tests independently to functional aspects of other models. """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mail",
        "sms",
        "sms_twilio",
        "test_orm",
    ],
    "data": [
        "security/ir.access.csv",
    ],
}

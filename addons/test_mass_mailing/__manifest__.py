{
    "name": "Mass Mail Tests",
    "version": "1.0",
    "category": "Marketing/Email Marketing",
    "sequence": 8765,
    "summary": "Mass Mail Tests: feature and performance tests for mass mailing",
    "description": """This module contains tests related to mass mailing. Those
are present in a separate module to use specific test models defined in
test_mail. """,
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "mass_mailing",
        "mass_mailing_sms",
        "sms_twilio",
        "test_mail",
        "test_mail_sms",
    ],
    "data": [
        "security/ir.access.csv",
    ],
}

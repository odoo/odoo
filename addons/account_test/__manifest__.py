# Copyright (c) 2011 CCI Connect asbl (http://www.cciconnect.be) All Rights Reserved.
#                       Philmer <philmer@cciconnect.be>

{
    "name": "Accounting Consistency Tests",
    "version": "1.0",
    "category": "Accounting/Accounting",
    "description": """
Asserts on accounting.
======================
With this module you can manually check consistencies and inconsistencies of accounting module from menu Reporting/Accounting/Accounting Tests.

You can write a query in order to create Consistency Test and you will get the result of the test 
in PDF format which can be accessed by Menu Reporting -> Accounting Tests, then select the test 
and print the report from Print button in header area.
""",
    "author": "Odoo S.A.",
    "license": "LGPL-3",
    "depends": [
        "account",
    ],
    "data": [
        "security/ir.access.csv",
        "views/accounting_assert_test_views.xml",
        "reports/accounting_assert_test_reports.xml",
        "data/accounting_assert_test_data.xml",
        "reports/report_account_test_templates.xml",
        "views/account_test_menus.xml",
    ],
}

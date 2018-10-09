# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 CCI Connect asbl (http://www.cciconnect.be) All Rights Reserved.
#                       Philmer <philmer@cciconnect.be>

{
    'name': 'Accounting Consistency Tests',
    'version': '1.0',
    'category': 'Accounting',
    'description': """
Asserts on accounting.
======================
With this module you can manually check consistencies and inconsistencies of accounting module from menu Reporting/Accounting/Accounting Tests.

You can write a query in order to create Consistency Test and you will get the result of the test 
in PDF format which can be accessed by Menu Reporting -> Accounting Tests, then select the test 
and print the report from Print button in header area.
""",
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/accounting_assert_test_views.xml',
        'report/accounting_assert_test_reports.xml',
        'data/accounting_assert_test_data.xml',
        'report/report_account_test_templates.xml',
    ],
    'active': False,
    'installable': True
}

# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 CCI Connect asbl (http://www.cciconnect.be) All Rights Reserved.
#                       Philmer <philmer@cciconnect.be>

{
    'name': 'Accounting Consistency Tests',
    'version': '1.0',
    'category': 'Accounting',
    'website': 'https://www.odoo.com/page/accounting',
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
        'account_test_view.xml',
        'account_test_report.xml',
        'account_test_data.xml',
        'views/report_accounttest.xml',
    ],
    'active': False,
    'installable': True
}

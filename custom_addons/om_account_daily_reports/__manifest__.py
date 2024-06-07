# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Cash Book, Day Book, Bank Book Financial Reports',
    'version': '17.0.1.1',
    'category': 'Invoicing Management',
    'summary': 'Cash Book, Day Book and Bank Book Report For Odoo 17',
    'description': 'Cash Book, Day Book and Bank Book Report For Odoo 17',
    'sequence': '10',
    'author': 'Odoo Mates',
    'license': 'LGPL-3',
    'company': 'Odoo Mates',
    'maintainer': 'Odoo Mates',
    'support': 'odoomates@gmail.com',
    'website': 'https://www.odoomates.tech',
    'depends': ['account', 'accounting_pdf_reports'],
    'live_test_url': '',
    'data': [
        'security/ir.model.access.csv',
        'views/om_daily_reports.xml',
        'wizard/daybook.xml',
        'wizard/cashbook.xml',
        'wizard/bankbook.xml',
        'report/reports.xml',
        'report/report_daybook.xml',
        'report/report_cashbook.xml',
        'report/report_bankbook.xml',
    ],
    'live_test_url': 'https://www.youtube.com/watch?v=PEh-an8iCO0',
    'images': ['static/description/banner.gif'],
}

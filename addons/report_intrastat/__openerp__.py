# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Intrastat Reporting',
    'version': '1.0',
    'category': 'Accounting & Finance',
    'description': """
A module that adds intrastat reports.
=====================================

This module gives the details of the goods traded between the countries of
European Union.""",
    'depends': ['base', 'product', 'delivery', 'stock', 'sale', 'purchase'],
    'data': [
        'security/ir.model.access.csv',
        'security/report_intrastat_security.xml',
        'report_intrastat_view.xml',
        'intrastat_report.xml',
        'report_intrastat_data.xml',
        'views/report_intrastatinvoice.xml',
    ],
    'demo': [],
    'test': ['../account/test/account_minimal_test.xml', 'test/report_intrastat_report.yml'],
    'installable': True,
    'auto_install': False,
}

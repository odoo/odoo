# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Intrastat Reporting',
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
        'data/report_intrastat_data.xml',
        'views/report_intrastat_views.xml',
        'views/product_views.xml',
        'views/res_country_views.xml',
        'report/intrastat_report.xml',
        'views/report_intrastatinvoice_templates.xml',
    ],
    'tests': ['../account/test/account_minimal_test.xml', 'test/report_intrastat_report.yml'],
}

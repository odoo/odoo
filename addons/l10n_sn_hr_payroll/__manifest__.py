# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) Optesis 2018 www.optesis.com

{
    'name': 'Paie Sénégalaise',
    'version': '13.0.1',
    'author': 'Optesis ',
    'category': 'Localization',
    'description': """
Senegal Payroll Rules.
=====================

    - Configuration of hr_payroll for Senegal localization
                    """,
    'website': 'http://www.optesis.com',
    'depends': ['hr_payroll', 'l10n_pcgo'],
    'data': [
        'security/ir.model.access.csv',
        'views/payroll_chart_template_views.xml',
        'views/multi_company_view.xml',
        'data/salary_rule_data.xml',
        'views/payroll_chart_template_views.xml',
        'views/multi_company_view.xml',
        'data/chart_data.xml',
        #'data/salary_rule_foreign_data.xml',
        'data/convention_collective_data.xml',
    ],

}

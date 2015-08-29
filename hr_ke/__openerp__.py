# -*- coding: utf-8 -*-
{
    'name': "HR for Kenya ",

    'summary': """
        Kenya Specific HR details for Employees, Employers and Contracts""",

    'description': """
        In this module, we are adding Kenya specific HR details and requirements for processing payroll. NSSF, NHIF, Next Of Kin, PAYE, HELB and others
    """,
    'images': ['static/description/hr.png'],
    'author': "Optima ICT Services LTD",
    'website': "http://www.optima.co.ke",
    'price': 400,
    'currency': 'EUR',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/openerp/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base', 'hr', 'hr_contract', 'account', 'hr_payroll', 'optima_social'],

    # always loaded
    'data': [
        'security/rules.xml',
        'security/groups.xml',
        'security/ir.model.access.csv',
	'data.xml',
	'hr_overtime_data.xml',
	'hr_advance_data.xml',
        'hr.xml',
	'hr_overtime.xml',
	'workflow.xml',
	'hr_advance.xml',
	'views/payslip.xml',
	'views/reports.xml',
	'views/muster_roll.xml',
	'views/hr_ke_muster_view.xml',
	'views/hr_ke_epay_view.xml',
	'views/hr_ke_nhif_view.xml',
	'views/hr_ke_nssf_view.xml',
	'views/epay_register.xml',
	'views/nhif_register.xml',
	'views/nssf_register.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo.xml',
    ],
}

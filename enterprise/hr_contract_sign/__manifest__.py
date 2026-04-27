# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Contract - Signature',
    'version': '1.0',
    'category': 'Human Resources',
    'summary': 'Manage your documents to sign in contracts',
    'depends': ['hr_contract', 'sign'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'wizard/hr_contract_sign_document_wizard_view.xml',
        'views/hr_contract_view.xml',
        'views/hr_employee_view.xml',
        'views/res_users_view.xml',
        'views/sign_request_views.xml',
        'views/mail_activity_plan_views.xml',
        'views/mail_activity_plan_template_views.xml',
        'report/hr_contract_history_report_views.xml',
        'data/hr_contract_sign_data.xml',
    ],
    'demo': [
        'data/hr_contract_sign_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

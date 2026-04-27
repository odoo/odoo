# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Recruitment - Signature',
    'version': '1.0',
    'category': 'Human Resources/Recruitment',
    'summary': 'Manage the signatures to send to your applicants',
    'depends': ['hr_recruitment', 'hr_contract_sign'],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_templates_chatter.xml',
        'wizard/hr_recruitment_sign_document_wizard_view.xml',
        'views/hr_applicant_views.xml',
    ],
    'assets': {
        'web.assets_tests': [
            'hr_recruitment_sign/static/tests/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

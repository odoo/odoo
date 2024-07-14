# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Payroll',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Store employee payslips in the Document app',
    'description': """
Employee payslips will be automatically integrated to the Document app.
""",
    'website': ' ',
    'depends': ['documents_hr', 'hr_payroll'],
    'data': [
        'data/documents_tag_data.xml',
        'data/mail_template_data.xml',
        'views/res_config_settings_views.xml',
        'views/hr_payroll_employee_declaration_views.xml',
        'security/security.xml'
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
    'post_init_hook': '_generate_payroll_document_folders',
}

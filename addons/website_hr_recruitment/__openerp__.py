{
    'name': 'Online Jobs',
    'category': 'Website',
    'version': '1.0',
    'summary': 'Job Descriptions And Application Forms',
    'description': """
Odoo Contact Form
====================

        """,
    'depends': ['website_partner', 'hr_recruitment', 'website_mail', 'website_form'],
    'data': [
        'security/website_hr_recruitment_security.xml',
        'security/ir.model.access.csv',
        'data/config_data.xml',
        'views/hr_job_views.xml',
        'views/hr_recruitment_views.xml',
        'views/website_hr_recruitment_templates.xml'
    ],
    'demo': [
        'data/hr_job_demo.xml',
    ],
    'installable': True,
}

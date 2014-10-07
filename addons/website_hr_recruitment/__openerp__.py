{
    'name': 'Online Jobs',
    'category': 'Website',
    'version': '1.0',
    'summary': 'Job Descriptions And Application Forms',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_partner', 'hr_recruitment', 'website_mail'],
    'data': [
        'security/ir.model.access.csv',
        'security/website_hr_recruitment_security.xml',
        'data/config_data.xml',
        'views/hr_job_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'data/hr_job_demo.xml',
    ],
    'installable': True,
}

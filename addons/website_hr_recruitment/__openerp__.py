{
    'name': 'Career Form',
    'category': 'Website',
    'version': '1.0',
    'summary': 'Job Position',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'hr', 'hr_recruitment'],
    'data': [
	'website_hr_recruitment_demo.xml',
	'website_hr_recruitment_data.xml',
        'views/website_hr_recruitment.xml',
        'security/ir.model.access.csv',
        'security/website_hr_recruitment_security.xml',
    ],
    'css':[
       'static/src/css/*.css'
      ],
    'installable': True,
}

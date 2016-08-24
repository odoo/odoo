{
    'name': 'Issues Form',
    'category': 'Project',
    'summary': 'Create Issues From Contact Form',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'depends': ['website_form','project_issue'],
    'data': [
        'data/website_issue_data.xml',
    ],
    'installable': True,
    'auto_install': True,
}

{
    'name': 'Issues Form',
    'category': 'Bridge',
    'summary': 'Create Issues From Contact Form',
    'version': '1.0',
    'description': """
OpenERP Contact Form
====================

        """,
    'author': 'OpenERP SA',
    'depends': ['website_form_builder','project_issue'],
    'data': [
        'data/website_issue_data.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'auto_install': True,
}

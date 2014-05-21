{
    'name' : 'LinkedIn Integration',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
OpenERP Web LinkedIn module.
============================
This module provides the Integration of the LinkedIn with OpenERP.
        """,
    'data': [
        'web_linkedin_view.xml',
        'views/web_linkedin.xml',
    ],
    'depends' : ['web','crm'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
}

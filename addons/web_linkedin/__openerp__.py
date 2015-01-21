{
    'name' : 'LinkedIn Integration',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
LinkedIn module
===============

Privides LinkedIn web integration.
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

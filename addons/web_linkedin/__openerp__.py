{
    'name' : 'LinkedIn Integration',
    'version': '0.1',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
        OpenERP Web LinkedIn module.
        This module provides the Integration of the LinkedIn with OpenERP.
        """,
    'data': [
        'web_linkedin_view.xml',
    ],
    'depends' : ['base'],
    'js': [
        'static/src/js/*.js'
        ],
    'css': [
        'static/src/css/*.css'
        ],
    'qweb': [
        'static/src/xml/*.xml'
        ],
    'installable': True,
    'auto_install': False,
}

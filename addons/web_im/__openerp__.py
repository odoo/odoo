{
    'name' : 'Instant Messaging',
    'version': '1.0',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
OpenERP Chat module
===================
Allows users to chat with each other.
        """,
    'data': [
        'security/ir.model.access.csv',
        'security/web_im_security.xml',
    ],
    'depends' : [],
    'js': ['static/src/js/*.js'],
    'css': ['static/src/css/*.css'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
}

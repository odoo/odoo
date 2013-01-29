{
    'name' : 'Live Support',
    'version': '1.0',
    'category': 'Tools',
    'complexity': 'easy',
    'description':
        """
OpenERP Live Support
====================
Allow to drop instant messaging widgets on any web page that will communicate with the current
server.
        """,
    'data': [
    ],
    'depends' : [],
    'js': ['static/src/js/*.js'],
    'css': ['static/src/css/*.css'],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
    'auto_install': False,
}

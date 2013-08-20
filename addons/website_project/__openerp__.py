{
'name': 'Public Project',
    'category': 'Website',
    'summary': 'Publish Your Public Projects',
    'version': '1.0',
    'description': """
OpenERP Blog
============

        """,
    'author': 'OpenERP SA',
    'depends': ['website', 'project'],
    'data': [
        'views/website_project.xml',
    ],
    'qweb': ['static/src/xml/*.xml'],
    'installable': True,
}

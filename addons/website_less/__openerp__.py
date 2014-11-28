{
    'name': 'Less compatibility layer for Website',
    'category': 'Website',
    'summary': 'Compatibility layer for using themes written in Less',
    'version': '1.0',
    'description': """
Compatibility layer for using themes written in Less with website 8.0
        """,
    'author': 'Odoo S.A.',
    'depends': ['website'],
    'data': [
        'views/snippets.xml',
        'views/themes.xml',
        'views/website_templates.xml',
        'views/website_backend_navbar.xml',
    ],
    'qweb': ['static/src/xml/website.backend.xml'],
    'installable': True,
    'application': False,
}

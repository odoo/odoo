{
    'name': 'Website Form Builder',
    'category': 'Website',
    'summary': 'Build custom web forms using the website builder',
    'version': '1.0',
    'description': """
Odoo Form Builder
====================

Allows you to build web forms on the website using the website builder.
        """,
    'depends': ['website', 'mail'],
    'data': [
        'views/assets.xml',
    ],
    'installable': True,
    'auto_install': False,
}

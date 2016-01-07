{
    'name': 'Website Theme Install',
    'description': "Propose to install a theme on website installation",
    'category': 'Website',
    'version': '1.0',
    'author': 'Odoo S.A.',
    'data': [
        'views/assets.xml',
        'views/views.xml',
    ],
    'depends': ['website'],
    'auto_install': True,
}

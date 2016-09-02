{
    'name': 'Bootswatch Theme',
    'summary': 'Support for Bootswatch themes in master',
    'description': 'This theme module is exclusively for master to keep the support of Bootswatch themes which were previously part of the website module in 8.0.',
    'category': 'Theme',
    'sequence': 900,
    'version': '1.0',
    'depends': ['website'],
    'data': [
        'views/theme.xml',
    ],
    'images': ['static/description/bootswatch.png'],
    'application': False,
}

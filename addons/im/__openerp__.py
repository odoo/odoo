{
    'name' : 'Instant Messaging Bus',
    'version': '1.0',
    'author': 'OpenERP SA',
    'category': 'Hidden',
    'complexity': 'easy',
    'description': "Instant Messaging bus",
    'depends': ['base', 'web'],
    'data': [
        'views/im.xml',
        'security/ir.model.access.csv',
    ],
}

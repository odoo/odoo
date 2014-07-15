{
    'name': 'Planner',
    'category': 'Hidden',
    'summary': 'Help to configure application',
    'version': '1.0',
    'description': """Application Planner""",
    'author': 'OpenERP SA',
    'depends': ['web'],
    'data': [
        'security/ir.model.access.csv',
        'views/planner.xml',
    ],

    'installable': True,
    'auto_install': True,
}

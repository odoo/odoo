{
    'name': 'Report',
    'category': 'Website',
    'summary': 'Report',
    'version': '1.0',
    'description': """
Report
        """,
    'author': 'OpenERP SA',
    'depends': ['base'],
    'data': [
        'views/paperformat_view.xml',
        'views/res_company_view.xml',
        'data/paperformat_defaults.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
}

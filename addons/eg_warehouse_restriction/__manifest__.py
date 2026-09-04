{
    "name": "Warehouse Restriction",

    'version': "16.0",

    'category': "Stock",

    "summary": "This app will Restrict selected warehouse for particular User",
    
    'author': 'INKERP',
    
    'website': "https://www.INKERP.com",

    "depends": ['stock'],
    
    "data": [
        "views/res_users_view.xml",
        "security/security.xml",
    ],

    'images': ['static/description/banner.png'],
    'license': "OPL-1",
    'installable': True,
    'application': True,
    'auto_install': False,
}

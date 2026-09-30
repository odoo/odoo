{
    'name': "ht_tools",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """
        Tools
    """,

    'author': "HT Land",
    'website': "https://htland.net.vn/",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/posts_views.xml',
        'views/group_views.xml',
        'views/menu_views.xml'
        
    ]
}


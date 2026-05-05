{
    'name': "Telesales",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """ Hỗ trợ sale phones
    """,

    'author': "HTLand",
    'website': "https://www.htland.net.vn",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'CRM/Sales',
    'version': '1.9',

    # any module necessary for this one to work correctly
    'depends': ['base'],

    # always loaded
    'data': [
        'views/groups.xml',
        'security/ir.model.access.csv',     
        'views/menu_views.xml',
        'views/estate_project_views.xml',
        'views/customer_views.xml',
        'views/QLNS.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3'
}


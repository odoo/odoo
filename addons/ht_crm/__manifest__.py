{
    'name': "HTLand CRM",

    'summary': "Short (1 phrase/line) summary of the module's purpose",

    'description': """ Thuộc về công ty HTLand
    """,

    'author': "HTLand",
    'website': "https://www.htland.net.vn",

    # Categories can be used to filter modules in modules listing
    # for the full list
    'category': 'CRM/Sales',
    'version': '1.9',

    # any module necessary for this one to work correctly
    'depends': ['base', 'web', 'mail'],

    'assets': {
        'web.assets_backend': [
            'ht_crm/static/src/css/phonebook.css',
        ],
    },

    # always loaded
    'data': [
        'views/groups.xml',
        'security/ir.model.access.csv',   
        'views/menu_views.xml',
        'views/rules/estate_project.xml',
        'views/rules/estate_property_unit.xml',
        'views/rules/sale_customers.xml',
        'views/rules/sale_phonebook.xml',
        'views/rules/sale_transaction.xml',
        'views/rules/employee_profile_sales.xml',
        'views/estate_project_view.xml',
        'views/estate_property_unit_type_view.xml',
        'views/estate_property_unit_view.xml',
        'views/estate_project_promotion_view.xml',
        'views/sale_customer_view.xml',
        'views/sale_phonebook_view.xml',
        'views/sale_phonebook_batch_view.xml',
        'views/sale_transaction_view.xml',
        'views/employee_profile_view.xml',
        'views/employee_profile_sales_view.xml',
        'views/action_reports.xml',
        'reports/layouts/external_layout_transaction.xml',
        'reports/customer_report.xml',
        'reports/estate_project.xml',
        'reports/estate_property_unit.xml',
        'reports/sale_transaction.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'license': 'LGPL-3'
}


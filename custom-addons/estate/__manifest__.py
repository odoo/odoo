{
    'name': "Real Estate",
    'version': '1.0',
    'category': 'Sales',
    'summary': 'Manage real estate properties',
    'description': """
        Real Estate Advertisement Module
    """,
    'license': 'LGPL-3',
    'depends': ['base'],
    'data': [
        'security/ir.model.access.csv',
        'data/estate.property.type.csv',
        'views/estate_actions.xml',
        'views/estate_views.xml',
        'views/estate_search.xml',
        'views/estate_kanban.xml',  
        'views/estate_property_type_views.xml',
        'views/estate_property_tag_views.xml',
        'views/estate_property_offer_views.xml',
        'views/estate_menu.xml',
        'views/inherited_user_views.xml',
        'report/estate_reports.xml',
        'report/estate_report_views.xml', 
    ],
    'demo': [
        'demo/estate_demo.xml',
        'demo/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

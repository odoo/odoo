{
    'name': "Real Estate Property",
    'version': '19.0.0.1.0',
    'summary': "Real Estate Property Management Module",
    'description': """
        A longer description of the module.
    """,
    'category': 'Uncategorized',
    'depends': ['base','account','sale_management','mail'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/property_menu.xml',
        'views/property_view.xml',
        'views/property_history_view.xml',
        'views/owner_view.xml',
        'views/tag_view.xml',
        'views/sale_order_view.xml',
        'wizard/change_state_wizard_view.xml',
        'reports/property_report.xml',
        # 'views/templates.xml',
    ],
    'demo': [
        # 'demo/demo_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'real_estate_property/static/src/css/property.css',
        ],
        'web.report_assets_common': [
            'real_estate_property/static/src/css/font.css',
        ]
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}

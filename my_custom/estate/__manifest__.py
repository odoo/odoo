{
    'name': 'Estate',
    'summary': 'Real Estate Management Module',
    'category': 'Sales',
    'depends': [
        'base'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/security.xml',
        'security/record_rules.xml',
        'views/estate_menus.xml',
        'views/estate_property_views.xml',
        'views/estate_property_tag_views.xml',
        'views/estate_property_type_views.xml',
        'views/estate_property_offer_views.xml',
        'views/res_users_view.xml',
        # 'views/estate_property_views_inherit.xml',
        # 'data/user_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}

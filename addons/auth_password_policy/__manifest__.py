{
    'name': "Password Policy",
    "summary": "Implements basic password policy configuration & check",
    'depends': ['base_setup', 'web'],
    'data': [
        'data/defaults.xml',
        'views/assets.xml',
        'views/res_users.xml',
        'views/res_config_settings_views.xml',
    ]
}

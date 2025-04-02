{
    'name': 'Certificate',
    'version': '0.1',
    'category': 'Hidden/Tools',
    'summary': 'Manage certificate',
    'installable': True,
    'data': [
        'views/certificate_views.xml',
        'views/key_views.xml',
        'views/action_menus.xml',
        'views/res_config_settings_view.xml',
        'security/ir.access.csv',
    ],
    'depends': ['base_setup'],
    'author': 'Odoo S.A.',
    'license': 'OEEL-1',
}


{
    'name': 'Odoo Debugpy',
    'summary': 'A debugger for python',
    'description': 
    """
    This module lets users start debugging from odoo web interface and has an example configuration to attach to it using vscode.
    """,
    'author': "mgite",
    # 'website': "https://example.com",
    'support': 'matemana2608@gmail.com',
    'license': 'GPL-3',
    'category': 'Tools',
    'version': '17.0.1.0.0',
    'images': ['static/description/wallpaper.png'],
    'external_dependencies': {
        'python': ['debugpy'],
    },
    "depends": [
        "base_setup",
    ],
    "data": [
        "views/res_config_settings_views.xml",
    ],
    "installable": True,
    "autoinstall": False,
    "application": False,
}

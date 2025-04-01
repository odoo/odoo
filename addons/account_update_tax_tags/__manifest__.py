{
    'name': 'Account - Allow updating tax grids',
    'category': 'Accounting/Accounting',
    'summary': 'Allow updating tax grids on existing entries',
    'version': '1.0',
    'description': """
    This module allows updating tax grids on existing accounting entries.
    In debug mode a button to update your entries' tax grids will be available
    in Accounting settings.
    This is typically useful after some legal changes were done on the tax report,
    requiring a new tax configuration.
    """,
    'depends': ['account'],
    'data': [
        'views/res_config_settings_views.xml',
        'wizard/account_update_tax_tags_wizard.xml',
        'security/ir.access.csv',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

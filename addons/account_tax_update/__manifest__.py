# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Account Tax Update",
    'description': """
    
    """,
    'category': 'Accounting/Accounting',
    'version': '1.0',
    'depends': [
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/account_tax_update_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}

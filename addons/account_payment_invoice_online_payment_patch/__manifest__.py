# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "Payment - Account / Invoice Online Payment Patch",
    'category': 'Accounting/Accounting',
    'depends': ['account_payment'],
    'auto_install': True,
    'data': [
        'data/ir_config_parameter.xml',

        'views/account_portal_templates.xml',

        'wizards/res_config_settings_views.xml',
    ],
    'license': 'LGPL-3',
}

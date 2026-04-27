# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Accounting',
    'version': '1.1',
    'category': 'Accounting/Accounting',
    'sequence': 30,
    'summary': 'Manage financial and analytic accounting',
    'description': """
Accounting Access Rights
========================
It gives the Administrator user access to all accounting features such as journal items and the chart of accounts.

It assigns manager and user access rights to the Administrator for the accounting application and only user rights to the Demo user.
""",
    'website': 'https://www.odoo.com/app/accounting',
    'depends': ['account_accountant'],
    'data': [
        'data/account_accountant_data.xml',
        'security/accounting_security.xml',
        'views/res_config_settings.xml',
        'views/partner_views.xml',
    ],
    'demo': ['demo/account_accountant_demo.xml'],
    'installable': True,
    'application': True,
    'post_init_hook': '_accounting_post_init',
    'uninstall_hook': "uninstall_hook",
    'license': 'OEEL-1',
    'assets': {
        'web.assets_backend': [
            'accountant/static/src/js/tours/accountant.js',
        ],
        'web.assets_tests': [
            'accountant/static/tests/tours/*',
        ],
    }
}

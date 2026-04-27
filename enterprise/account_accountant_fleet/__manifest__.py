# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Accounting/Fleet bridge',
    'category': 'Accounting/Accounting',
    'summary': 'Manage accounting with fleet features',
    'version': '1.0',
    'depends': ['account_fleet', 'account_accountant'],
    'assets': {
        'web.assets_backend': [
            'account_accountant_fleet/static/src/components/**/*',
        ],
    },
    'license': 'OEEL-1',
    'auto_install': True,
}

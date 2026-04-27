# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employment Hero Payroll',
    'countries': ['au', 'nz', 'gb', 'sg', 'my'],
    'category': 'Accounting',
    'depends': [
        'account_accountant',
    ],
    'version': '1.0',
    'description': """
Employment Hero Payroll Integration
This Module will synchronise all payrun journals from Employment Hero to Odoo.
    """,
    'author': 'Odoo S.A.,Inspired Software Pty Limited',
    'contributors': [
        'Michael Villamar',
        'Jacob Oldfield',
    ],
    'website': 'https://www.inspiredsoftware.com.au',
    'data': [
        'data/ir_cron_data.xml',
        'views/account_views.xml',
        'views/res_config_settings.xml',
    ],
    'installable': True,
    'license': 'OEEL-1',
}

# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Term - Days end of month on the',
    'version': '1.0',
    'category': 'Accounting/Accounting',
    'description': """
Bridge module to add a new payment term - Days end of month on the
""",
    'website': 'https://www.odoo.com/app/invoicing',
    'depends': ['account'],
    'data': [
        'views/account_payment_term_views.xml',
    ],
    'demo': [
        'demo/account_payment_term_demo.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

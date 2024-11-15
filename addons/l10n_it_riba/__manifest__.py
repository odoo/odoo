{
    'name': 'Italy - Bank Receipts (Ri.Ba.)',
    'icon': '/l10n_it/static/description/icon.png',
    'version': '0.1',
    'depends': [
        'l10n_it',
        'base_iban',
        'account_batch_payment'
    ],
    'auto_install': ['l10n_it'],
    'author': 'Odoo',
    'description': """
Manages Bank Receipts (Ri.Ba.).
    """,
    'category': 'Accounting/Localizations',
    'website': 'http://www.odoo.com/',
    'data': [
        'data/account_payment_method_data.xml',
    ],
    'demo': [],
    'post_init_hook': False,
    'license': 'LGPL-3',
}

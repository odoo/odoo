{
    'name': 'Account Online Payment',
    'summary': 'Initiate online payments',
    'description': 'This module allows customers to pay their invoices online using various payment methods.',
    'depends': ['account_online_synchronization', 'account_batch_payment', 'account_iso20022'],
    'data': [
        'data/actions.xml',
        'views/account_batch_payment_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'account_online_payment/static/src/components/**/*',
        ],
    },
    'auto_install': True,
    'license': 'LGPL-3',
}

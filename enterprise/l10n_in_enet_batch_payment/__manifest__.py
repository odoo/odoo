{
    'name': "India ENet Batch Payment CSV Generator",
    'summary': """Export batch payments as ENet files""",
    'category': 'Accounting/Accounting',
    'description': """
Generate csv files for vendor batch payments,which can be uploaded to the bank for ENet payments.
    """,
    'version': '1.0',
    'depends': ['account_batch_payment', 'l10n_in'],
    'data': [
        "security/ir.model.access.csv",
        "data/bank_template.xml",
        "data/enet_payment_methods.xml",
        "views/account_journal_views.xml",
        "views/account_batch_payment_views.xml",
    ],
    'assets': {
        'web.assets_backend': [
            'l10n_in_enet_batch_payment/static/src/many2one_avatar_field.js',
        ]
    },
    'license': 'OEEL-1',
}

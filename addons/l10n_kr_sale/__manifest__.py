{
    'name': "Republic of Korea - Sales",
    'countries': ['kr'],
    'category': 'Accounting/Localizations/Sale',
    'description': """
Bridge module between the Korean localization and Sales, exposing the proof of issuance
(발행 증빙) on sales orders and propagating it to the invoices created from them.
    """,
    'depends': ['sale', 'l10n_kr'],
    'auto_install': True,
    'data': [
        'views/sale_order_views.xml',
    ],
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

{
    'name': "Egypt E-Receipts (POS)",
    'summary': "Submit POS receipts to the Egyptian Tax Authority",
    'description': """
Egypt E-Receipts (POS)
======================
Submits POS sales receipts to the Egyptian Tax Authority (ETA) eReceipt API
after order payment. Prints a compliant QR at the top of the receipt when
accepted, prints THIS IS NOT A LEGAL DOCUMENT when not, and tracks ETA state
per-order. Refunds made from the POS ask for a reason, printed on the receipt
together with the reference of the refunded order.
""",
    'author': "Odoo S.A.",
    'category': 'Accounting/Localizations/EDI',
    'license': 'LGPL-3',
    'depends': ['point_of_sale', 'l10n_eg_edi_eta'],
    'countries': ['eg'],
    'data': [
        'views/res_config_settings_views.xml',
        'views/pos_order_views.xml',
        'views/pos_payment_method_views.xml',
        'receipt/pos_order_receipt.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'l10n_eg_edi_pos/static/src/**/*',
        ],
    },
    'auto_install': True,
}

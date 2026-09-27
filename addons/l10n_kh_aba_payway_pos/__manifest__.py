{
    'name': 'ABA PayWay QR Payment for POS',
    'countries': ['KH'],
    'version': '1.0',
    'summary': 'Display dynamic payment QR codes on screen and printed bills.',
    'description': """
        Let customers pay using QR codes in Odoo POS.\n
        This plugin supports multiple payment QR formats (ABA KHQR, WeChat Pay, Alipay) by displaying the payment QR on the POS customer screen or printed bill (only applicable for POS restaurant modules).

        To set up: \n
        Go to POS module → Configuration → Payment Methods \n
        Click Add New, then in the Integration section: \n
        1. Choose Bank App (QR Code) \n
        2. Select a QR format: ABA KHQR, WeChat Pay, or Alipay \n
        3. Make sure to use the same name for the Payment Method Name \n
        4. Configure the Bank Journal as usual \n

        Want to print the payment QR on bills? Turn on “Allow QR on bills” (works with Restaurant POS only). \n
        Then select the Point of Sales of your choice - the payment option will now appear on both the cashier and customer screens during checkout.
    """,
    'author': 'Odoo S.A., ABA Bank',
    'category': 'Point of Sale',
    'depends': [
        'point_of_sale',
        # TODO: Remove dependancy on restaurant
        'pos_restaurant',
        'l10n_kh_aba_payway',
    ],
    'auto_install': True,
    'data': [
        'views/pos_payment_method_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'aba_payway_qr_payment_pos_odoo/static/src/app/**/*',
            'aba_payway_qr_payment_pos_odoo/static/src/img/**/*',
            'aba_payway_qr_payment_pos_odoo/static/src/fonts/**/*',
            'aba_payway_qr_payment_pos_odoo/static/src/style/**/*'
        ],
        'point_of_sale.customer_display_assets': [
            'aba_payway_qr_payment_pos_odoo/static/src/customer_display/**/*',
            'aba_payway_qr_payment_pos_odoo/static/src/img/**/*',
            'aba_payway_qr_payment_pos_odoo/static/src/fonts/**/*',
            'aba_payway_qr_payment_pos_odoo/static/src/style/**/*'
        ]
    },
    'installable': True,
    'license': 'LGPL-3',
}

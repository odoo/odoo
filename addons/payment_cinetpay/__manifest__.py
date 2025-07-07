{
    'name': 'Payment CinetPay',
    'version': '1.0',
    'category': 'Payment',
    'summary': 'Module de paiement via CinetPay pour Odoo',
    'description': """
        Ce module permet d'intégrer la passerelle de paiement CinetPay dans Odoo,
        permettant aux utilisateurs de traiter les paiements via cette plateforme.
    """,
    'author': 'Sunsoft',
    'website': 'https://www.sunsoft.com',
    'depends': ['website_sale', 'payment', 'point_of_sale'],
    'data': [
        'views/buy_now_form.xml',
        'views/payment_history_template.xml',
        'views/payment_thank_you.xml',
        'views/product_buy_now.xml',
        'views/website_sale_cinetpay_templates.xml',
        'data/payment_provider_data.xml',
        #'views/payment_history_menu.xml',
        'views/pos_payment_method_form_inherit.xml',
        #'views/assets.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'payment_cinetpay/static/src/js/buy_now.js',
        ],
        'point_of_sale._assets_pos': [
            'payment_cinetpay/static/src/js/cinetpay_payment.js',
        ],
        'point_of_sale._assets': [
            'payment_cinetpay/static/src/js/cinetpay_pos.js',
        ],   },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}

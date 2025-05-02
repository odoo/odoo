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
    'depends': ['payment'],
    'data': [
        'views/buy_now_form.xml',
        'views/product_buy_now.xml',
        'views/website_sale_cinetpay_templates.xml',
            ],
    'assets': {
        'web.assets_frontend': [
            'payment_cinetpay/static/src/js/buy_now.js',
        ],
    },
    'installable': True,
    'auto_install': False,
    'application': True,
    'license': 'LGPL-3',
}

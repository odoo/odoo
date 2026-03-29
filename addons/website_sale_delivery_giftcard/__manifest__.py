{
    'name': 'Website Sale Delivery Giftcard',
    'category': 'Website/Website',
    'version': '1.0',
    'depends': ['website_sale_delivery', 'website_sale_gift_card'],
    'installable': True,
    'auto_install': True,
    'assets': {
        'web.assets_tests': [
            'website_sale_delivery_giftcard/static/tests/**/*',
        ],
    },
    'license': 'LGPL-3',
}

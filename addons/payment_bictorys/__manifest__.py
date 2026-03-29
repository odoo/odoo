# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Payment Provider: Bictorys (Wave, Orange Money, Card)',
    'version': '1.0',
    'category': 'Accounting/Payment Providers',
    'sequence': 350,
    'summary': "A West African payment provider for online and Point of Sale payments.",
    'description': "One integration, all popular payment methods, your payments in real time.",
    'author': "NIASS Ibrahima",
    'website': "https://www.linkedin.com/in/ibrahima-niass-969265132",
    'depends': ['payment', 'point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'views/payment_provider_views.xml',
        'views/payment_transaction_views.xml',
        'views/pos_payment_method_views.xml',
        'data/payment_provider_data.xml',
        'views/payment_templates.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'uninstall_hook': 'uninstall_hook',
    'assets': {
        'web.assets_frontend': [
            'payment_bictorys/static/src/js/payment_form.js',
        ],
        'point_of_sale._assets_pos': [
            'payment_bictorys/static/src/js/bictorys_payment_method.js',
            'payment_bictorys/static/src/js/bictorys_pos_store.js',
            'payment_bictorys/static/src/xml/bictorys_payment_method.xml',
            'payment_bictorys/static/src/css/bictorys_pos.css',
        ],
    },
    'images': ['static/description/cover.png'],
    'license': 'LGPL-3',
    'installable': True,
    'auto_install': False,
    # 'price': 69.98,
    # 'currency': 'EUR',
    'maintainer': 'NIASS Ibrahima',
    'support': 'ibrahimaniassbb@gmail.com',
}
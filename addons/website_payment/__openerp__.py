# -*- coding: utf-8 -*-

{
    'name': 'Payment: Website Bridge Integration',
    'category': 'Website',
    'summary': 'Payment: Website Bridge Module',
    'version': '1.0',
    'description': """Bridge module between the payment acquirer module and the
    website module.""",
    'author': 'OpenERP SA',
    'depends': [
        'website',
        'payment_acquirer',
    ],
    'data': [
    ],
    'js': [
        'static/lib/jquery.payment/jquery.payment.js',
        'static/src/js/website_payment.js'
    ],
    'css': [
        'static/src/css/website_payment.css'
    ],
}

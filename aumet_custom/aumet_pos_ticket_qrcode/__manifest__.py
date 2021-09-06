{
    'name': ' Aumet  Pos Ticket QR Code',
    'version': '14.0.1.0.0',
    'description': """
        QR Code Add Receipt POS
    """,
    'depends': ['point_of_sale'],
    'data': [
        'views/PosConfig.xml'
    ],
    'demo': [
    ],
    'qweb': [
        'static/src/xml/Screens/ReceiptScreen/OrderReceipt.xml'
    ],
    'installable': True,
    'application': True,
    'auto_install': False
}

# -*- coding: utf-8 -*-
{
    'name': "POS multi uom price",
    'summary': 'POS Price per unit of measure',
    'category': 'Point of Sale',
    'version': '14.0.1.0.1',
    'license': "AGPL-3",
    'description': """
        With this module you can sell your products with different units of measure in POS.
    """,

    'author': "ehuerta _at_ ixer.mx",
    'depends': ['point_of_sale', 'flexipharmacy'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_view.xml',
        'views/pos_multi_uom_price_templates.xml',
    ],
    'qweb': [
        'static/src/xml/multi_uom_price.xml',
    ],
    'images': [
        'static/description/POS_multi_uom_price.png',
    ],
    'installable': True,
    'auto_install': False,
}

# -*- coding: utf-8 -*-


{
    'name': 'Odoo Product Tree',
    'version': '1.0',
    'category': 'OdTree',
    'sequence': 14,
    'license':'LGPL-3',
    'description': """
    display product in a product category tree
    """,
    'author': 'openliu',
    'website': 'http://www.openliu.com',
    'images': [],
    'depends': ['odtree','product'],
    'qweb': [

    ],
    'data': [
        'views/product_view.xml'
    ],
    'installable': True,
    'auto_install': False,
    'application': True,
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

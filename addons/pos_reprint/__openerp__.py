# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Point of Sale Receipt Reprinting',
    'version': '1.0',
    'category': 'Point of Sale',
    'sequence': 6,
    'summary': 'Allow cashier to reprint receipts',
    'description': """

=======================

Allow cashier to reprint receipts

""",
    'author': 'Odoo SA',
    'depends': ['point_of_sale'],
    'data': [
        'views/templates.xml',
        'views/views.xml',
    ],
    'qweb': [
        'static/src/xml/reprint.xml',
    ],
    'installable': True,
    'website': 'https://www.odoo.com/page/point-of-sale',
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

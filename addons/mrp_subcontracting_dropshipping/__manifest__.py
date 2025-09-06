# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Dropship and Subcontracting Management',
    'version': '0.1',
    'category': 'Supply Chain/Purchase',
    'description': """
This bridge module allows to manage subcontracting with the dropshipping module.
    """,
    'depends': ['mrp_subcontracting', 'stock_dropshipping'],
    'data': [
        'data/mrp_subcontracting_dropshipping_data.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'author': 'Odoo S.A.',
    'license': 'LGPL-3',
}

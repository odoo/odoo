# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'POS Pricer',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Display and change your products information on electronic Pricer tags',
    'data': [
        'security/ir.model.access.csv',
        'views/pricer_tag_views.xml',
        'views/pricer_store_views.xml',
        'views/pos_pricer_configuration.xml',
        'views/product_views.xml',
        'data/pricer_ir_cron.xml',
    ],
    'depends': ['product', 'point_of_sale'],
    'installable': True,
    'license': 'OEEL-1',
}

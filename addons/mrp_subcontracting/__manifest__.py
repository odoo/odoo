# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "mrp_subcontracting",
    'version': '0.1',
    'summary': "Subcontract Productions",
    'description': "",
    'website': 'https://www.odoo.com/page/manufacturing',
    'category': 'Manufacturing/Manufacturing',
    'depends': ['mrp', 'contacts'],
    'data': [
        'data/mrp_subcontracting_data.xml',
        'views/stock_warehouse_views.xml',
        'views/stock_picking_views.xml',
        'views/mrp_bom_views.xml',
    ],
    'post_init_hook': '_create_subcontracting_rules',
}

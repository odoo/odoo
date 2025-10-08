# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Estate',
    'depends': [
        'base',
    ],
    'installable': True,
    'application': True,
    'data': [
        'security/ir.model.access.csv',
        # 'views/estate_property_view_tree.xml',
        'views/estate_property_views.xml',
        'views/estate_menus.xml',
    ],
}

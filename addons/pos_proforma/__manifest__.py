# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "pos_proforma",
    'category': "Hidden",
    'summary': 'Allow the user to use pro forma order',

    'description': """
        The user is able to use pro forma order
    """,

    'depends': ['pos_restaurant'],

    'data': [
        'security/ir.model.access.csv',
        'views/pro_forma_order_views.xml',
    ],
    'post_init_hook': '_init_ir_sequence_on_config',
    'assets': {
        'point_of_sale.assets': [
            'pos_proforma/static/src/js/**/*',
        ]
    },
    'installable': True,
    'license': 'LGPL-3',
}

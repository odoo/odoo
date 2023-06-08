# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'mk_fiscal_printer',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Fiscal ePOS Printers in PoS',
    'description': "",
    'depends': ['point_of_sale'],
    'data': [
        'views/pos_config_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'point_of_sale.assets': [
            'mk_fiscal_printer/static/src/js/lib/**/*',
            'mk_fiscal_printer/static/src/js/**/*',
        ],
    },
    'license': 'LGPL-3',
}

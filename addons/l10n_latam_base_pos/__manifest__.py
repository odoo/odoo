# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Latam localization for TPV',
    'version': '16.0.1.0.0',
    'category': 'POS',
    'author': 'TRESCLOUD',
    'maintainer': 'TRESCLOUD',
    'website': 'http://www.trescloud.com',
    'description': '''''',
    'depends': [
        'base',
        'l10n_latam_base',
        'point_of_sale',
    ],
    'data': [],
    'license': 'OPL-1',
    'assets': {
        'point_of_sale.assets': [
            # CSS
            'l10n_latam_base_pos/static/src/css/global.css',
            # JS
            'l10n_latam_base_pos/static/src/js/**/*.js',
            # XML
            'l10n_latam_base_pos/static/src/xml/**/*',
        ],
    },
    'installable': True,
    'auto_install': True,
}

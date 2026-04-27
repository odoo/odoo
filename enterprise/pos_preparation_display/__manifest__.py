# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'PoS Preparation Display',
    'version': '1.0.0',
    'category': 'Sales/Point of Sale',
    'sequence': 7,
    'summary': 'Display Orders for Preparation stage.',
    'depends': ['point_of_sale'],
    'data': [
        'security/ir.model.access.csv',
        'security/preparation_display_security.xml',
        'views/preparation_display_assets_index.xml',
        'views/preparation_display_view.xml',
        'wizard/preparation_display_reset_wizard.xml',
        'data/preparation_display_cron.xml',
    ],
    'installable': True,
    'auto_install': True,
    'assets': {
        'pos_preparation_display.assets': [
            # 'preparation_display' bootstrap customization layer
            'web/static/src/scss/functions.scss',
            'pos_preparation_display/static/src/scss/primary_variables.scss',
            ("include", "point_of_sale.base_app"),
            'web/static/src/webclient/webclient.scss',
            'web/static/src/webclient/icons.scss',
            'point_of_sale/static/src/utils.js',

            'mail/static/src/core/common/sound_effects_service.js',
            'point_of_sale/static/src/overrides/sound_effects_service.js',
            'pos_preparation_display/static/src/app/**/*',
        ],
        'pos_preparation_display.assets_tour_tests': [
            ("include", "point_of_sale.base_tests"),
            'pos_preparation_display/static/tests/tours/preparation_display/**/*',
        ],
        'point_of_sale._assets_pos': [
            'pos_preparation_display/static/src/override/**/*.js',
        ],
        'web.assets_tests': [
            'pos_preparation_display/static/tests/tours/point_of_sale/**/*',
        ],
    },
    'license': 'OEEL-1',
}

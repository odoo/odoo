# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "RTC - real time communication",
    'depends': ['base_setup'],
    'category': 'Hidden',
    'license': 'LGPL-3',
    'data': [
        'views/res_config_settings_views.xml',
    ],
    'assets': {
        'rtc.assets_odoo_sfu': [
            'rtc/static/lib/odoo_sfu/odoo_sfu.js',
        ],
    }
}

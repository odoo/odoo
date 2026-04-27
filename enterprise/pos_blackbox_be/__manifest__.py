# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'Belgian Registered Cash Register',
    'version': '1.0',
    'category': 'Sales/Point of Sale',
    'sequence': 6,
    'summary': 'Implements the registered cash system, adhering to guidelines by FPS Finance.',
    'description': """
Belgian Registered Cash Register
================================

This module turns the Point Of Sale module into a certified Belgian cash register.

More info:
  * http://www.systemedecaisseenregistreuse.be/
  * http://www.geregistreerdkassasysteem.be/

Legal
-----
**The use of pos_blackbox_be sources is only certified on odoo.com SaaS platform
for version 17.0** Contact Odoo SA before installing pos_blackbox_be module.

An obfuscated and certified version of the pos_blackbox_be may be provided on
requests for on-premise installations.
No modified version is certified and supported by Odoo SA.
    """,
    'depends': ['pos_iot', 'l10n_be', 'web_enterprise', 'pos_hr', 'pos_restaurant', 'pos_discount'],
    'data': [
        'data/data.xml',
        'security/ir.model.access.csv',
        'views/hr_employee_views.xml',
        'views/pos_blackbox_be_views.xml',
        'views/pos_daily_reports.xml',
        'views/pos_order_views.xml',
        'views/res_config_settings_views.xml',
        'views/res_users_views.xml'
    ],
    'demo': [
        'data/demo.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_blackbox_be/static/src/**/*',
        ],
    },
    'post_init_hook': '_set_tax_on_work_in_out',
    'installable': True,
    'license': 'OEEL-1',
}

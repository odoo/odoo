# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Mass Mailing euro compliance',
    'version': '1.0',
    'category': 'Marketing/Email Marketing',
    'sequence': 5,
    'depends': [
        'mass_mailing', 'link_tracker',
    ],
    'data': [
        'views/mailing_mailing_views.xml',
        'views/res_config_settings_views.xml',
    ],
    'installable': True,
    'license': 'LGPL-3',
}

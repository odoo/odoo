# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Odoo referral program bridge with portal (Deprecated)",
    'summary': """Allow you to refer your friends to Odoo and get rewards - Deprecated""",
    'category': 'Hidden',
    'version': '0.1',
    'depends': ['website', 'odoo_referral'],
    'data': [
        'views/referral_template.xml',
    ],
    'auto_install': False, # As deprecated,
    'license': 'LGPL-3',
}

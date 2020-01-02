# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': "Odoo referral internal",

    'summary': """
        Internal module for the odoo referral program""",
    'description': """
        Manage queries made to display the status of the odoo referral program on all the clients' DBs""",
    'category': 'Hidden',
    'version': '0.1',
    'depends': ['website', 'website_crm_referral'],
    'data': [
        'views/referral_template.xml',
    ],
    'auto_install': False,
}

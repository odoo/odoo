# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'school cron',
    'version': '14.0.1.0.0',
    'summary': '--------------------',
    'sequence': 12,
    'description': """ORM methods""",
    'category': '',
    'depends': [
            'base',
            'contacts',
            'partner_autocomplete',
            'sale_management',
            'purchase',
    ],
    'website': 'https://www.xyz.com',
    'data': [
        'data/partner_data.xml',
        'data/user_data.xml',
        'security/record_rules.xml',
        'wizard/register_redirect_wizard_views.xml',
        'wizard/course_add_wizard_action_menu_views.xml',
        'views/course_views.xml',
        'views/respartner_views.xml',
        'views/batch_views.xml',
        'views/registration_views.xml',
        'views/sale_order_views.xml',
        'views/batch_inherits_views.xml',
        'security/ir.model.access.csv',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}


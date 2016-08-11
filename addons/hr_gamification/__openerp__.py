# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
{
    'name': 'HR Gamification',
    'version': '1.0',
    'category': 'Human Resources',
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['gamification', 'hr'],
    'description': """Use the HR ressources for the gamification process.

The HR officer can now manage challenges and badges.
This allow the user to send badges to employees instead of simple users.
Badge received are displayed on the user profile.
""",
    'data': [
        'security/ir.model.access.csv',
        'security/gamification_security.xml',
        'wizard/grant_badge.xml',
        'views/gamification.xml',
        'views/hr_gamification.xml',
    ],
    'auto_install': True,
}

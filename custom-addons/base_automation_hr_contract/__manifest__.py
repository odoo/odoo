# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Automation Rules based on Employee Contracts',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Bridge to add contract calendar on automation rules
===================================================
    """,
    'depends': ['base_automation', 'hr_contract'],
    'data': [
        'views/base_automation_views.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

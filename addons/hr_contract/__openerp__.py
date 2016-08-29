# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Employee Contracts',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Add all information on the employee form to manage contracts.
=============================================================

    * Contract
    * Place of Birth,
    * Medical Examination Date
    * Company Vehicle

You can assign several contracts per employee.
    """,
    'website': 'https://www.odoo.com/page/employees',
    'depends': ['base_action_rule', 'hr'],
    'data': [
        'security/ir.model.access.csv',
        'data/hr_contract_data.xml',
        'views/base_action_rule_views.xml',
        'views/hr_contract_views.xml',
    ],
    'demo': [],
    'installable': True,
    'auto_install': False,
}

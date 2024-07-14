# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Planning Contract',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 50,
    'summary': 'Planning integration with contracts',
    'depends': ['planning', 'hr_contract'],
    'description': """
Planning integration with hr contract

With this module, planning take into account employee's contracts for
slots planification and allocated hours.
""",
    'demo': [
        'data/hr_contract_demo.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

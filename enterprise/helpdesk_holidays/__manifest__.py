# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Time Off',
    'version': '1.0',
    'category': 'Hidden',
    'sequence': 50,
    'summary': 'Helpdesk integration with holidays',
    'depends': ['helpdesk', 'hr_holidays_gantt'],
    'data': [
        'views/helpdesk_team_view.xml',
    ],
    'description': """
Helpdesk integration with time off
""",
    'auto_install': True,
    'license': 'OEEL-1',
}

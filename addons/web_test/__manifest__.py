# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Web Test',
    'category': 'Hidden',
    'version': '1.0',
    'description': """Odoo Web Test""",
    'depends': ['base', 'web', 'hr_work_entry'],
    'auto_install': True,
    'data': [
        'security/ir.model.access.csv',
        'views/calendar_views.xml',
    ],
    'license': 'LGPL-3',
    'author': 'Odoo',
}

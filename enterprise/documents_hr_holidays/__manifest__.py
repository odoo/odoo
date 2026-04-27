# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Time Off',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Store employee\'s time off documents in the Document app',
    'description': """
Time off documents will be automatically integrated to the Document app.
""",
    'depends': ['documents_hr', 'hr_holidays'],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

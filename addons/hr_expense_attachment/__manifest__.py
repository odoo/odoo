# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': "HR Expense Attachment",
    'summary': """HR Expense Attachment""",
    'description': """
        - Allows you to attach document directly on record form.
    """,
    'category': 'Employees',
    'version': '1.0',
    'depends': ['hr_expense'],
    'qweb': ['static/src/xml/*.xml'],
    'auto_install': True,
    'installable': True,
    'data': [
        'views/hr_expense_attachment.xml',
        'views/hr_expense_attach_template.xml'
    ],
    'license': 'OEEL-1',
}

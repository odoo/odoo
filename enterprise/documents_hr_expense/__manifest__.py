# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - Expense',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Store expense documents in the Document app',
    'description': """
Expense documents will be automatically integrated to the Document app.
    """,
    'depends': ['documents', 'hr_expense_extract'],
    'data': [
        'data/ir_actions_server_data.xml',
        'views/hr_expense_views.xml',
    ],
    'demo': [
        'demo/documents_document_demo.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
}

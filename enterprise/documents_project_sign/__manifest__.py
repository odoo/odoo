# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents Project Sign',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Sign documents attached to tasks',
    'description': """
Adds an action to sign documents attached to tasks.
""",
    'website': ' ',
    'depends': ['documents_project', 'documents_sign'],
    'data': [
        'data/ir_actions_server_data.xml',
    ],
    'installable': True,
    'auto_install': True,
    'license': 'OEEL-1',
}

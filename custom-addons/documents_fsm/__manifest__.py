# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Documents - FSM',
    'version': '1.0',
    'category': 'Productivity/Documents',
    'summary': 'Avoid auto-enabling the documents feature on fsm projects',
    'description': """
Avoid auto-enabling the documents feature on fsm projects.
    """,
    'depends': ['documents_project', 'industry_fsm'],
    'auto_install': True,
    'license': 'OEEL-1',
    'post_init_hook': '_documents_fsm_post_init'
}

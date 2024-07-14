# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Helpdesk Knowledge',
    'version': '1.0',
    'category': 'Hidden',
    'summary': 'Helpdesk integration with knowledge',
    'depends': [
        'website_helpdesk',
        'knowledge',
    ],
    'description': """
Helpdesk integration with knowledge
""",
    'data': [
        'views/helpdesk_templates.xml',
        'views/helpdesk_views.xml',
        'data/knowledge_data.xml',
    ],
    'auto_install': True,
    'license': 'OEEL-1',
    'assets': {
        'web.assets_tests': [
            'website_helpdesk_knowledge/static/tests/tours/**/*',
        ],
    },
}

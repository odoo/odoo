# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Knowledge Website',
    'summary': 'Publish your articles',
    'version': '1.0',
    'depends': ['knowledge', 'website'],
    'data': [
        'security/ir.model.access.csv',
        'security/ir_rule.xml',
        'views/knowledge_views.xml',
        'views/knowledge_templates_frontend.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': True,
    'license': 'LGPL-3',
    'assets': {
        'web.assets_backend': [
            'website_knowledge/static/src/js/knowledge_controller.js',
            'website_knowledge/static/src/client_actions/website_preview/website_preview.js',
        ]
    },
}
